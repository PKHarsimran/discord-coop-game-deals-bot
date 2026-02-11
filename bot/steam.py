from __future__ import annotations

from typing import Set

import requests

STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

COOP_CATEGORY_KEYWORDS: Set[str] = {
    "co-op",
    "online co-op",
    "lan co-op",
    "shared/split screen co-op",
}


def is_coop_app(appid: str, timeout: int = 20) -> bool:
    """
    Validates co-op support based on Steam categories list in appdetails.
    """
    params = {"appids": str(appid), "l": "en", "cc": "us"}
    r = requests.get(STEAM_APPDETAILS_URL, params=params, timeout=timeout)
    r.raise_for_status()

    payload = r.json()
    app_key = str(appid)
    if app_key not in payload or not payload[app_key].get("success"):
        return False

    data = payload[app_key].get("data") or {}
    categories = data.get("categories") or []

    cat_desc = {
        str(c.get("description", "")).strip().lower()
        for c in categories
        if isinstance(c, dict)
    }

    if any(kw in cat_desc for kw in COOP_CATEGORY_KEYWORDS):
        return True

    # fallback handles slight variations
    return any("co-op" in desc for desc in cat_desc)
