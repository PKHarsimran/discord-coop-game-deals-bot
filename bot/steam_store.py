from __future__ import annotations

from typing import Any, Dict, List

import requests

from .models import Deal

STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories"
STEAM_STORE_ICON = "https://store.cloudflare.steamstatic.com/public/shared/images/header/logo_steam.svg"


def fetch_steam_specials(upper_price: float, timeout: int = 20) -> List[Deal]:
    params = {"cc": "us", "l": "en"}
    r = requests.get(STEAM_FEATURED_URL, params=params, timeout=timeout)
    r.raise_for_status()
    payload: Dict[str, Any] = r.json()

    specials = payload.get("specials", {}).get("items", [])

    deals: List[Deal] = []
    for item in specials:
        try:
            appid = str(item.get("id", "")).strip()
            if not appid:
                continue

            final_cents = int(item.get("final_price", 0) or 0)
            initial_cents = int(item.get("original_price", 0) or 0)
            sale_price = final_cents / 100
            normal_price = (initial_cents / 100) if initial_cents > 0 else sale_price
            savings_pct = float(item.get("discount_percent", 0) or 0)

            if sale_price <= 0 or sale_price >= upper_price:
                continue

            title = str(item.get("name", "")).strip()
            if not title:
                continue

            deals.append(
                Deal(
                    deal_id=f"steam-special-{appid}",
                    title=title,
                    sale_price=sale_price,
                    normal_price=normal_price,
                    savings_pct=savings_pct,
                    store_id="steam-direct",
                    store_name="Steam",
                    store_icon=STEAM_STORE_ICON,
                    steam_app_id=appid,
                    thumb=(str(item.get("small_capsule_image", "")).strip() or None),
                    buy_url=f"https://store.steampowered.com/app/{appid}/",
                    source_label="Steam",
                )
            )
        except Exception:
            continue

    return deals
