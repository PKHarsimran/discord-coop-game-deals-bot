from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


def _to_bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _to_int(v: str | None, default: int) -> int:
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


def _to_float(v: str | None, default: float) -> float:
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def _to_csv_list(v: str | None) -> List[str]:
    if not v:
        return []
    return [x.strip() for x in v.split(",") if x.strip()]


def _to_csv_set(v: str | None) -> Set[str]:
    return set(_to_csv_list(v))


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str
    discord_webhook_username: str

    max_price: float
    max_posts_per_run: int
    only_steam_redeemable: bool

    allowed_store_ids: List[str]
    exclude_keywords: Set[str]

    posted_cache_file: Path
    embed_color: int

    # Role ping (opt-in)
    ping_role_on_post: bool
    discord_role_id: str


def load_settings() -> Settings:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    username = os.getenv("DISCORD_WEBHOOK_USERNAME", "Co-op Deals Bot").strip() or "Co-op Deals Bot"

    max_price = _to_float(os.getenv("MAX_PRICE", "10.00"), 10.0)
    max_posts = _to_int(os.getenv("MAX_POSTS_PER_RUN", "10"), 10)
    only_steam = _to_bool(os.getenv("ONLY_STEAM_REDEEMABLE", "true"), True)

    allowed_store_ids = _to_csv_list(os.getenv("ALLOWED_STORE_IDS", ""))

    # Default excludes (override by setting EXCLUDE_KEYWORDS)
    default_excludes = {"hentai", "nsfw", "sex", "porn", "simulator"}
    env_excludes = os.getenv("EXCLUDE_KEYWORDS")
    exclude_keywords = _to_csv_set(env_excludes) if env_excludes is not None else default_excludes

    posted_cache_file = Path(os.getenv("POSTED_CACHE_FILE", "data/posted_deals.json"))

    # Embed color (Discord integer color)
    embed_color = int(os.getenv("EMBED_COLOR", str(0x57F287)), 0)

    # Role ping
    ping_role_on_post = _to_bool(os.getenv("PING_ROLE_ON_POST", "false"), False)
    discord_role_id = os.getenv("DISCORD_ROLE_ID", "").strip()

    return Settings(
        discord_webhook_url=webhook,
        discord_webhook_username=username,
        max_price=max_price,
        max_posts_per_run=max_posts,
        only_steam_redeemable=only_steam,
        allowed_store_ids=allowed_store_ids,
        exclude_keywords=exclude_keywords,
        posted_cache_file=posted_cache_file,
        embed_color=embed_color,
        ping_role_on_post=ping_role_on_post,
        discord_role_id=discord_role_id,
    )
