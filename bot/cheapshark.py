from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .models import Deal

CHEAPSHARK_DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_STORES_URL = "https://www.cheapshark.com/api/1.0/stores"


def fetch_stores(timeout: int = 20) -> Dict[str, Dict[str, Any]]:
    """
    Returns mapping: store_id -> store object containing storeName and images paths.
    """
    r = requests.get(CHEAPSHARK_STORES_URL, timeout=timeout)
    r.raise_for_status()
    raw = r.json()

    stores: Dict[str, Dict[str, Any]] = {}
    for s in raw:
        sid = str(s.get("storeID", "")).strip()
        if sid:
            stores[sid] = s
    return stores


def _store_icon_url(store_obj: Dict[str, Any]) -> Optional[str]:
    images = store_obj.get("images") or {}
    icon_rel = images.get("icon")
    if not icon_rel:
        return None
    # CheapShark icons are typically relative paths like "/img/stores/icons/0.png"
    return f"https://www.cheapshark.com{icon_rel}"


def fetch_deals(
    upper_price: float,
    steamworks_only: bool,
    allowed_store_ids: Optional[List[str]],
    store_map: Dict[str, Dict[str, Any]],
    timeout: int = 20,
) -> List[Deal]:
    """
    Fetch deal candidates from CheapShark.
    Note: You MUST still hard-filter locally by price in main.py.
    """
    params: Dict[str, str] = {
        "upperPrice": f"{upper_price:.2f}",
        "pageSize": "60",
        "onSale": "1",
        "sortBy": "Deal Rating",
        "desc": "1",
    }
    if steamworks_only:
        params["steamworks"] = "1"
    if allowed_store_ids:
        params["storeID"] = ",".join(allowed_store_ids)

    r = requests.get(CHEAPSHARK_DEALS_URL, params=params, timeout=timeout)
    r.raise_for_status()
    raw = r.json()

    deals: List[Deal] = []
    for item in raw:
        try:
            store_id = str(item.get("storeID", "")).strip()
            store_obj = store_map.get(store_id, {})
            store_name = str(store_obj.get("storeName", "")).strip() or f"Store {store_id}"
            store_icon = _store_icon_url(store_obj)

            deal = Deal(
                deal_id=str(item.get("dealID", "")).strip(),
                title=str(item.get("title", "")).strip(),
                sale_price=float(item.get("salePrice", "0") or 0),
                normal_price=float(item.get("normalPrice", "0") or 0),
                savings_pct=float(item.get("savings", "0") or 0),
                store_id=store_id,
                store_name=store_name,
                store_icon=store_icon,
                steam_app_id=(str(item.get("steamAppID")).strip() if item.get("steamAppID") else None),
                thumb=(str(item.get("thumb")).strip() if item.get("thumb") else None),
                buy_url=f"https://www.cheapshark.com/redirect?dealID={str(item.get('dealID', '')).strip()}",
                source_label="CheapShark",
            )
            if deal.deal_id and deal.title and deal.sale_price > 0:
                deals.append(deal)
        except Exception:
            continue

    return deals
