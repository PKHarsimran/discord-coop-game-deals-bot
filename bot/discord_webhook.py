from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from .models import Deal


def build_embed(deal: Deal, embed_color: int) -> Dict[str, Any]:
    steam_url = deal.steam_url
    main_url = steam_url or deal.cheapshark_url

    price_line = f"**${deal.sale_price:.2f}** ~~${deal.normal_price:.2f}~~  (**-{deal.savings_pct:.0f}%**)"
    store_line = f"Store: **{deal.store_name}**"

    links_value = f"[Buy deal]({deal.cheapshark_url})"
    if steam_url:
        links_value += f" • [Steam]({steam_url})"

    embed: Dict[str, Any] = {
        "title": deal.title[:256],
        "url": main_url,
        "description": f"{price_line}\n{store_line}"[:4096],
        "color": embed_color,
        "fields": [{"name": "Links", "value": links_value, "inline": False}],
        "footer": {"text": "Source: CheapShark • Filter: Co-op + <$10"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Prefer game thumb, fall back to store icon
    if deal.thumb:
        embed["thumbnail"] = {"url": deal.thumb}
    elif deal.store_icon:
        embed["thumbnail"] = {"url": deal.store_icon}

    return embed


def post_embeds(
    webhook_url: str,
    username: str,
    content: str,
    embeds: List[Dict[str, Any]],
    timeout: int = 20,
) -> None:
    """
    Discord: max 10 embeds per message.
    """
    payload = {
        "content": content,
        "username": username,
        "embeds": embeds[:10],
        "allowed_mentions": {"parse": []},
    }
    r = requests.post(webhook_url, json=payload, timeout=timeout)
    r.raise_for_status()


def post_deals(webhook_url: str, username: str, deals: List[Deal], embed_color: int) -> None:
    embeds = [build_embed(d, embed_color) for d in deals]
    post_embeds(
        webhook_url=webhook_url,
        username=username,
        content="🎮 **Tonight’s Co-op Deals (Under $10)**",
        embeds=embeds,
    )
