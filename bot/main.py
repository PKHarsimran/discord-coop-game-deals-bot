from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Set

import requests

from .cheapshark import fetch_deals, fetch_stores
from .config import load_settings
from .discord_webhook import post_deals
from .steam import is_coop_app


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


def main() -> None:
    s = load_settings()

    if not s.discord_webhook_url:
        raise SystemExit("Missing DISCORD_WEBHOOK_URL. Set it as a GitHub Secret.")

    print("=== Co-op Deals Bot ===")
    print(f"Max price: < ${s.max_price:.2f} | Max posts/run: {s.max_posts_per_run}")
    print(f"Steam redeemable filter: {s.only_steam_redeemable}")
    print(f"Allowed stores: {s.allowed_store_ids if s.allowed_store_ids else 'ALL'}")
    print(f"Exclude keywords: {sorted(s.exclude_keywords)}")
    print(f"Cache file: {s.posted_cache_file}")
    print(f"Role ping enabled: {s.ping_role_on_post} | Role ID: {s.discord_role_id or 'none'}")

    stores = fetch_stores()
    posted = load_posted_ids(s.posted_cache_file)

    candidates = fetch_deals(
        upper_price=s.max_price,
        steamworks_only=s.only_steam_redeemable,
        allowed_store_ids=s.allowed_store_ids if s.allowed_store_ids else None,
        store_map=stores,
    )
    print(f"Fetched candidates: {len(candidates)} | Already posted: {len(posted)}")

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

    post_deals(
        webhook_url=s.discord_webhook_url,
        username=s.discord_webhook_username,
        deals=selected,
        embed_color=s.embed_color,
        role_id_to_ping=role_id,
    )
    print(f"🚀 Posted {len(selected)} deal(s) to Discord")

    for d in selected:
        posted.add(d.deal_id)

    save_posted_ids(s.posted_cache_file, posted)
    print("💾 Cache updated")


if __name__ == "__main__":
    main()
