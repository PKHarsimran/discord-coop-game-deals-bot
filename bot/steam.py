from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


from .http_client import get_json

STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_APPREVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
STEAM_CURRENT_PLAYERS_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
STEAMSPY_APPDETAILS_URL = "https://steamspy.com/api.php"

COOP_CATEGORY_KEYWORDS = {
    "co-op",
    "online co-op",
    "lan co-op",
    "shared/split screen co-op",
}

CATEGORY_TO_TAG = {
    "co-op": "Co-op",
    "online co-op": "Online Co-op",
    "lan co-op": "LAN Co-op",
    "shared/split screen co-op": "Split-Screen Co-op",
}


class SteamCoopCache:
    def __init__(self, path: Path):
        self.path = path
        self._data: Dict[str, Dict[str, Any]] = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data = raw
            except Exception:
                self._data = {}

    def get(self, appid: str) -> Optional[Dict[str, Any]]:
        v = self._data.get(str(appid))
        return v if isinstance(v, dict) else None

    def set(self, appid: str, value: Dict[str, Any]) -> None:
        self._data[str(appid)] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


def fetch_coop_metadata(appid: str, timeout: int = 20) -> Tuple[bool, List[str]]:
    payload = get_json(STEAM_APPDETAILS_URL, params={"appids": str(appid), "l": "en", "cc": "us"}, timeout=timeout)
    app_key = str(appid)
    if app_key not in payload or not payload[app_key].get("success"):
        return False, []

    data = payload[app_key].get("data") or {}
    categories = data.get("categories") or []

    cat_desc = {
        str(c.get("description", "")).strip().lower()
        for c in categories
        if isinstance(c, dict)
    }

    tags = [label for key, label in CATEGORY_TO_TAG.items() if key in cat_desc]
    is_coop = any(kw in cat_desc for kw in COOP_CATEGORY_KEYWORDS) or any("co-op" in desc for desc in cat_desc)
    return is_coop, tags


def fetch_review_summary(appid: str, timeout: int = 20) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    url = STEAM_APPREVIEWS_URL.format(appid=appid)
    payload = get_json(
        url,
        params={"json": "1", "language": "all", "num_per_page": "0", "purchase_type": "all"},
        timeout=timeout,
    )
    q = payload.get("query_summary") or {}
    text = q.get("review_score_desc")
    pct = q.get("review_score")
    total = q.get("total_reviews")
    return (
        str(text).strip() if text else None,
        int(pct) if isinstance(pct, int) else None,
        int(total) if isinstance(total, int) else None,
    )


def fetch_current_players(appid: str, timeout: int = 20) -> Optional[int]:
    payload = get_json(
        STEAM_CURRENT_PLAYERS_URL,
        params={"appid": str(appid)},
        timeout=timeout,
    )
    response = payload.get("response") if isinstance(payload, dict) else None
    count = response.get("player_count") if isinstance(response, dict) else None
    return int(count) if isinstance(count, int) else None


def fetch_steamspy_stats(appid: str, timeout: int = 20) -> Tuple[Optional[int], Optional[str]]:
    payload = get_json(
        STEAMSPY_APPDETAILS_URL,
        params={"request": "appdetails", "appid": str(appid)},
        timeout=timeout,
    )

    if not isinstance(payload, dict):
        return None, None

    ccu = payload.get("ccu")
    owners = payload.get("owners")
    return (
        int(ccu) if isinstance(ccu, int) else None,
        str(owners).strip() if owners else None,
    )
