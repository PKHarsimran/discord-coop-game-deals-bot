from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Deal:
    deal_id: str
    title: str
    sale_price: float
    normal_price: float
    savings_pct: float
    store_id: str
    store_name: str
    store_icon: Optional[str]
    steam_app_id: Optional[str]
    thumb: Optional[str]
    buy_url: Optional[str] = None
    source_label: str = "CheapShark"

    @property
    def cheapshark_url(self) -> str:
        return f"https://www.cheapshark.com/redirect?dealID={self.deal_id}"

    @property
    def deal_url(self) -> str:
        return self.buy_url or self.cheapshark_url

    @property
    def steam_url(self) -> Optional[str]:
        if not self.steam_app_id:
            return None
        return f"https://store.steampowered.com/app/{self.steam_app_id}/"
