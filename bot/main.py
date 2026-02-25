from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

import requests

from .cheapshark import fetch_deals, fetch_stores
from .config import load_settings
from .discord_webhook import post_deals
from .models import Deal
from .steam import (
    SteamCoopCache,
    fetch_coop_metadata,
    fetch_current_players,
    fetch_review_summary,
    fetch_steamspy_stats,
)
from .steam_store import fetch_steam_specials

LOGGER = logging.getLogger("coop_deals_bot")


def configure_logging(level: str) -> None:
    resolved = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def load_posted_ids(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("dealIDs"), list):
            return set(str(x) for x in data["dealIDs"])
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception as e:
        LOGGER.warning("Failed to load posted cache file %s: %s", path, e)
    return set()


def save_posted_ids(path: Path, posted: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps({"dealIDs": sorted(posted)}, indent=2), encoding="utf-8")
    tmp_path.replace(path)


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


def _digest_title(mode: str, max_price: float, profile_name: str) -> str:
    prefix = f"[{profile_name}] " if profile_name != "default" else ""
    if mode == "weekend":
        return f"{prefix}🎉 **Weekend Co-op Picks (Under ${max_price:.0f})**"
    if mode == "budget":
        return f"{prefix}💸 **Ultra-Budget Co-op Picks (Under ${max_price:.0f})**"
    return f"{prefix}🎮 **Tonight's Co-op Deals (Under ${max_price:.0f})**"


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


def _franchise_key(title: str, words: int) -> str | None:
    normalized = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    tokens = [
        t
        for t in normalized.split()
        if (len(t) > 1 or t.isdigit()) and t not in {"edition", "bundle", "pack", "dlc"}
    ]
    if not tokens:
        return None
    return " ".join(tokens[:words])


def _passes_review_threshold(
    review_percent: object,
    review_count: object,
    min_review_percent: int,
    min_review_count: int,
) -> bool:
    if min_review_percent <= 0 and min_review_count <= 0:
        return True
    if not isinstance(review_percent, int) or not isinstance(review_count, int):
        return False
    return review_percent >= min_review_percent and review_count >= min_review_count


def _fetch_optional_popularity_stats(appid: str) -> tuple[int | None, int | None, str | None]:
    current_players = None
    steamspy_ccu = None
    steamspy_owners = None

    try:
        current_players = fetch_current_players(appid)
    except requests.RequestException as e:
        LOGGER.warning("Steam current players check failed for appid=%s: %s", appid, e)

    try:
        steamspy_ccu, steamspy_owners = fetch_steamspy_stats(appid)
    except requests.RequestException as e:
        LOGGER.warning("SteamSpy stats check failed for appid=%s: %s", appid, e)

    return current_players, steamspy_ccu, steamspy_owners


def _build_metrics_summary(metrics: "RunMetrics") -> str:
    cheapshark_count = metrics.source_counts.get("cheapshark", 0)
    steam_direct_count = metrics.source_counts.get("steam_direct", 0)

    return "\n".join(
        [
            "📊 Deal run summary",
            (
                "• Fetched: "
                f"{metrics.fetched_total} "
                f"(CheapShark: {cheapshark_count}, Steam Direct: {steam_direct_count})"
            ),
            f"• Posted: {metrics.posted_count}",
            (
                "• Filtered: "
                f"price={metrics.filtered_price}, "
                f"discount={metrics.filtered_discount}, "
                f"keywords={metrics.filtered_keyword}, "
                f"missing_appid={metrics.filtered_missing_appid}, "
                f"non_coop={metrics.filtered_non_coop}, "
                f"reviews={metrics.filtered_reviews}, "
                f"already_posted={metrics.filtered_already_posted}, "
                f"dup_appid={metrics.filtered_duplicate_appid}, "
                f"dup_franchise={metrics.filtered_duplicate_franchise}"
            ),
            f"• Metadata errors: {metrics.metadata_errors}",
        ]
    )


@dataclass
class RunMetrics:
    fetched_total: int = 0
    filtered_price: int = 0
    filtered_discount: int = 0
    filtered_keyword: int = 0
    filtered_missing_appid: int = 0
    filtered_non_coop: int = 0
    filtered_reviews: int = 0
    filtered_already_posted: int = 0
    filtered_duplicate_appid: int = 0
    filtered_duplicate_franchise: int = 0
    metadata_errors: int = 0
    posted_count: int = 0
    source_counts: Dict[str, int] = field(default_factory=dict)


def main() -> None:
    s = load_settings()
    configure_logging(s.log_level)

    if not s.discord_webhook_url:
        LOGGER.warning("Missing DISCORD_WEBHOOK_URL. Set it as a GitHub Secret. Skipping run.")
        return

    LOGGER.info("=== Co-op Deals Bot ===")
    LOGGER.info(
        "Profile=%s max_price=<%.2f max_posts=%d mode=%s min_discount=%.1f min_review_pct=%d min_review_count=%d",
        s.profile_name,
        s.max_price,
        s.max_posts_per_run,
        s.digest_mode,
        s.min_discount_percent,
        s.min_review_percent,
        s.min_review_count,
    )

    metrics = RunMetrics()

    try:
        stores = fetch_stores()
    except requests.RequestException as e:
        LOGGER.warning("Failed to fetch store catalog from CheapShark: %s", e)
        return

    filtered_stores = _filter_store_map(stores, s)
    if not filtered_stores:
        LOGGER.info("No stores matched current allow/exclude filters. Nothing posted.")
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
        LOGGER.warning("Failed to fetch deals from CheapShark: %s", e)
        cheapshark_candidates = []

    if s.include_steam_direct_specials:
        try:
            steam_direct_candidates = fetch_steam_specials(s.max_price)
        except requests.RequestException as e:
            LOGGER.warning("Failed to fetch specials from Steam Store API: %s", e)
            steam_direct_candidates = []
    else:
        steam_direct_candidates = []

    metrics.source_counts["cheapshark"] = len(cheapshark_candidates)
    metrics.source_counts["steam_direct"] = len(steam_direct_candidates)

    candidates = cheapshark_candidates + steam_direct_candidates
    metrics.fetched_total = len(candidates)
    enriched: List[Deal] = []

    for d in candidates:
        if d.sale_price >= s.max_price:
            metrics.filtered_price += 1
            continue

        if d.savings_pct < s.min_discount_percent:
            metrics.filtered_discount += 1
            continue

        if any(k in d.title.lower() for k in s.exclude_keywords):
            metrics.filtered_keyword += 1
            continue

        if not d.steam_app_id:
            metrics.filtered_missing_appid += 1
            continue

        cached = steam_cache.get(d.steam_app_id)
        try:
            if cached is None:
                is_coop, tags = fetch_coop_metadata(d.steam_app_id)
                review_summary, review_pct, review_count = fetch_review_summary(d.steam_app_id)
                current_players, steamspy_ccu, steamspy_owners = _fetch_optional_popularity_stats(d.steam_app_id)
                cached = {
                    "is_coop": is_coop,
                    "coop_tags": tags,
                    "review_summary": review_summary,
                    "review_percent": review_pct,
                    "review_count": review_count,
                    "current_players": current_players,
                    "steamspy_ccu": steamspy_ccu,
                    "steamspy_owners": steamspy_owners,
                }
                steam_cache.set(d.steam_app_id, cached)

            if not bool(cached.get("is_coop")):
                metrics.filtered_non_coop += 1
                continue

            review_pct = cached.get("review_percent")
            review_count = cached.get("review_count")
            if not _passes_review_threshold(review_pct, review_count, s.min_review_percent, s.min_review_count):
                metrics.filtered_reviews += 1
                continue

            d.coop_tags = list(cached.get("coop_tags") or [])
            d.review_summary = cached.get("review_summary")
            d.review_percent = review_pct
            d.review_count = review_count
            d.current_players = cached.get("current_players")
            d.steamspy_ccu = cached.get("steamspy_ccu")
            d.steamspy_owners = cached.get("steamspy_owners")
            d.reason = _reason_for_deal(d, s.price_sweet_spot)
            enriched.append(d)
        except requests.RequestException as e:
            metrics.metadata_errors += 1
            LOGGER.warning("Steam metadata check failed for %s (appid=%s): %s", d.title, d.steam_app_id, e)

    steam_cache.save()

    ranked = sorted(
        enriched,
        key=lambda d: _score_deal(d, s.price_sweet_spot, d.deal_id in posted),
        reverse=True,
    )

    selected: List[Deal] = []
    seen_appids: Set[str] = set()
    seen_franchises: Set[str] = set()
    for d in ranked:
        if d.deal_id in posted:
            metrics.filtered_already_posted += 1
            continue
        if d.steam_app_id and d.steam_app_id in seen_appids:
            metrics.filtered_duplicate_appid += 1
            continue
        if s.franchise_dedupe_enabled:
            fk = _franchise_key(d.title, s.franchise_dedupe_words)
            if fk and fk in seen_franchises:
                metrics.filtered_duplicate_franchise += 1
                continue
        else:
            fk = None

        selected.append(d)
        if d.steam_app_id:
            seen_appids.add(d.steam_app_id)
        if fk:
            seen_franchises.add(fk)

        if len(selected) >= s.max_posts_per_run:
            break

    if not selected:
        LOGGER.info("No new co-op deals found. Nothing posted.")
        LOGGER.info("Run metrics: %s", metrics)
        return

    role_id = s.discord_role_id if (s.ping_role_on_post and s.discord_role_id) else None
    metrics.posted_count = len(selected)

    try:
        post_deals(
            webhook_url=s.discord_webhook_url,
            username=s.discord_webhook_username,
            deals=selected,
            embed_color=s.embed_color,
            message_title=_digest_title(s.digest_mode, s.max_price, s.profile_name),
            role_id_to_ping=role_id,
            metrics_summary=_build_metrics_summary(metrics),
        )
    except requests.RequestException as e:
        LOGGER.warning("Failed to post deals to Discord webhook: %s", e)
        return

    LOGGER.info("Posted %d deal(s) to Discord", len(selected))

    for d in selected:
        posted.add(d.deal_id)

    save_posted_ids(s.posted_cache_file, posted)
    LOGGER.info("Cache updated")
    LOGGER.info("Run metrics: %s", metrics)


if __name__ == "__main__":
    main()
