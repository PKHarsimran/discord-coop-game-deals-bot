from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

import requests

from .cheapshark import fetch_deals, fetch_stores
from .config import load_settings
from .discord_webhook import post_deals
from .models import Deal
from .steam import SteamCoopCache, fetch_coop_metadata, fetch_review_summary
from .steam_store import fetch_steam_specials


def load_posted_ids(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("dealIDs"), list):
            return set(str(x) for x in data["dealIDs"])
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        pass
    return set()


def save_posted_ids(path: Path, posted: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dealIDs": sorted(posted)}, indent=2), encoding="utf-8")


def _normalize_store_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _filter_store_map(stores: Dict[str, dict], s) -> Dict[str, dict]:
    allowed_ids = set(s.allowed_store_ids)
    excluded_ids = set(s.excluded_store_ids)

    allowed_names = {_normalize_store_name(n) for n in s.allowed_store_names}
    excluded_names = {_normalize_store_name(n) for n in s.excluded_store_names}

    selected = stores
    if allowed_ids or allowed_names:
        selected = {
            sid: st
            for sid, st in selected.items()
            if sid in allowed_ids
            or _normalize_store_name(str(st.get("storeName", ""))) in allowed_names
        }

    if excluded_ids or excluded_names:
        selected = {
            sid: st
            for sid, st in selected.items()
            if sid not in excluded_ids
            and _normalize_store_name(str(st.get("storeName", ""))) not in excluded_names
        }

    return selected


def _digest_title(mode: str, max_price: float) -> str:
    if mode == "weekend":
        return f"🎉 **Weekend Co-op Picks (Under ${max_price:.0f})**"
    if mode == "budget":
        return f"💸 **Ultra-Budget Co-op Picks (Under ${max_price:.0f})**"
    return f"🎮 **Tonight's Co-op Deals (Under ${max_price:.0f})**"


def _score_deal(d: Deal, sweet_spot: float, was_posted: bool) -> float:
    discount_score = d.savings_pct
    cheap_bonus = max(0.0, (sweet_spot - d.sale_price) * 4.0)
    coop_bonus = float(len(d.coop_tags or [])) * 6.0
    review_bonus = float((d.review_percent or 0) / 5.0)
    recency_penalty = 35.0 if was_posted else 0.0
    return discount_score + cheap_bonus + coop_bonus + review_bonus - recency_penalty


def _reason_for_deal(d: Deal, sweet_spot: float) -> str:
    reasons: List[str] = []
    if d.savings_pct >= 75:
        reasons.append(f"massive -{d.savings_pct:.0f}% discount")
    if d.sale_price <= sweet_spot:
        reasons.append(f"in the sweet spot under ${sweet_spot:.2f}")
    if d.coop_tags and len(d.coop_tags) > 1:
        reasons.append("supports multiple co-op modes")
    if d.review_summary and d.review_percent and d.review_percent >= 80:
        reasons.append(f"strong Steam sentiment ({d.review_percent}%)")
    return ", ".join(reasons) if reasons else "solid co-op value pick"


def main() -> None:
    s = load_settings()

    if not s.discord_webhook_url:
        print("⚠️ Missing DISCORD_WEBHOOK_URL. Set it as a GitHub Secret. Skipping run.")
        return

    print("=== Co-op Deals Bot ===")
    print(f"Max price: < ${s.max_price:.2f} | Max posts/run: {s.max_posts_per_run}")
    print(f"Steam redeemable filter: {s.only_steam_redeemable}")
    print(f"Include Steam direct specials source: {s.include_steam_direct_specials}")
    print(f"Digest mode: {s.digest_mode} | Sweet spot: ${s.price_sweet_spot:.2f}")

    try:
        stores = fetch_stores()
    except requests.RequestException as e:
        print(f"⚠️ Failed to fetch store catalog from CheapShark: {e}")
        return

    filtered_stores = _filter_store_map(stores, s)
    if not filtered_stores:
        print("No stores matched current allow/exclude filters. Nothing posted.")
        return

    posted = load_posted_ids(s.posted_cache_file)
    steam_cache = SteamCoopCache(s.steam_cache_file)

    try:
        cheapshark_candidates = fetch_deals(
            upper_price=s.max_price,
            steamworks_only=s.only_steam_redeemable,
            allowed_store_ids=list(filtered_stores.keys()),
            store_map=filtered_stores,
        )
    except requests.RequestException as e:
        print(f"⚠️ Failed to fetch deals from CheapShark: {e}")
        cheapshark_candidates = []

    if s.include_steam_direct_specials:
        try:
            steam_direct_candidates = fetch_steam_specials(s.max_price)
        except requests.RequestException as e:
            print(f"⚠️ Failed to fetch specials from Steam Store API: {e}")
            steam_direct_candidates = []
    else:
        steam_direct_candidates = []

    candidates = cheapshark_candidates + steam_direct_candidates
    enriched: List[Deal] = []

    for d in candidates:
        if d.sale_price >= s.max_price:
            continue

        if any(k in d.title.lower() for k in s.exclude_keywords):
            continue

        if not d.steam_app_id:
            continue

        cached = steam_cache.get(d.steam_app_id)
        try:
            if cached is None:
                is_coop, tags = fetch_coop_metadata(d.steam_app_id)
                review_summary, review_pct, review_count = fetch_review_summary(d.steam_app_id)
                cached = {
                    "is_coop": is_coop,
                    "coop_tags": tags,
                    "review_summary": review_summary,
                    "review_percent": review_pct,
                    "review_count": review_count,
                }
                steam_cache.set(d.steam_app_id, cached)

            if not bool(cached.get("is_coop")):
                continue

            d.coop_tags = list(cached.get("coop_tags") or [])
            d.review_summary = cached.get("review_summary")
            d.review_percent = cached.get("review_percent")
            d.review_count = cached.get("review_count")
            d.reason = _reason_for_deal(d, s.price_sweet_spot)
            enriched.append(d)
        except requests.RequestException as e:
            print(f"⚠️ Steam metadata check failed for {d.title} (appid={d.steam_app_id}): {e}")

    steam_cache.save()

    ranked = sorted(
        enriched,
        key=lambda d: _score_deal(d, s.price_sweet_spot, d.deal_id in posted),
        reverse=True,
    )

    selected: List[Deal] = []
    for d in ranked:
        if d.deal_id in posted:
            continue
        selected.append(d)
        if len(selected) >= s.max_posts_per_run:
            break

    if not selected:
        print("No new co-op deals found. Nothing posted.")
        return

    role_id = s.discord_role_id if (s.ping_role_on_post and s.discord_role_id) else None

    try:
        post_deals(
            webhook_url=s.discord_webhook_url,
            username=s.discord_webhook_username,
            deals=selected,
            embed_color=s.embed_color,
            message_title=_digest_title(s.digest_mode, s.max_price),
            role_id_to_ping=role_id,
        )
    except requests.RequestException as e:
        print(f"⚠️ Failed to post deals to Discord webhook: {e}")
        return

    print(f"🚀 Posted {len(selected)} deal(s) to Discord")

    for d in selected:
        posted.add(d.deal_id)

    save_posted_ids(s.posted_cache_file, posted)
    print("💾 Cache updated")


if __name__ == "__main__":
    main()
