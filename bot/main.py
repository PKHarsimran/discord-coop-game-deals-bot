from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Set

import requests

from .cheapshark import fetch_deals, fetch_stores
from .config import load_settings
from .discord_webhook import post_deals
from .steam import is_coop_app
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

def main() -> None:
    s = load_settings()

    if not s.discord_webhook_url:
        print("⚠️ Missing DISCORD_WEBHOOK_URL. Set it as a GitHub Secret. Skipping run.")
        return

    print("=== Co-op Deals Bot ===")
    print(f"Max price: < ${s.max_price:.2f} | Max posts/run: {s.max_posts_per_run}")
    print(f"Steam redeemable filter: {s.only_steam_redeemable}")
    print(f"Include Steam direct specials source: {s.include_steam_direct_specials}")
    print(f"Allowed store IDs: {s.allowed_store_ids if s.allowed_store_ids else 'ALL'}")
    print(f"Allowed store names: {s.allowed_store_names if s.allowed_store_names else 'ALL'}")
    print(f"Excluded store IDs: {s.excluded_store_ids if s.excluded_store_ids else 'NONE'}")
    print(f"Excluded store names: {s.excluded_store_names if s.excluded_store_names else 'NONE'}")
    print(f"Exclude keywords: {sorted(s.exclude_keywords)}")
    print(f"Cache file: {s.posted_cache_file}")
    print(f"Role ping enabled: {s.ping_role_on_post} | Role ID: {s.discord_role_id or 'none'}")

    if s.ping_role_on_post and not s.discord_role_id:
        print("⚠️ PING_ROLE_ON_POST=true but DISCORD_ROLE_ID is empty. Continuing without role mention.")

    try:
        stores = fetch_stores()
    except requests.RequestException as e:
        print(f"⚠️ Failed to fetch store catalog from CheapShark: {e}")
        return

    filtered_stores = _filter_store_map(stores, s)
    if not filtered_stores:
        print("No stores matched current allow/exclude filters. Nothing posted.")
        return

    print(f"Store catalog size: {len(stores)} | Active stores after filters: {len(filtered_stores)}")

    posted = load_posted_ids(s.posted_cache_file)

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
    print(
        f"Fetched candidates: {len(candidates)} "
        f"(CheapShark={len(cheapshark_candidates)}, SteamDirect={len(steam_direct_candidates)}) "
        f"| Already posted: {len(posted)}"
    )

    selected = []
    for d in candidates:
        # HARD filter: guarantee < MAX_PRICE
        if d.sale_price >= s.max_price:
            continue

        if d.deal_id in posted:
            continue

        title_l = d.title.lower()
        if any(k in title_l for k in s.exclude_keywords):
            continue

        # Need steam_app_id to validate co-op
        if not d.steam_app_id:
            continue

        try:
            if is_coop_app(d.steam_app_id):
                selected.append(d)
                print(f"✅ {d.title} | ${d.sale_price:.2f} | {d.store_name}")
        except requests.RequestException as e:
            print(f"⚠️ Steam check failed for {d.title} (appid={d.steam_app_id}): {e}")

        time.sleep(0.15)

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
