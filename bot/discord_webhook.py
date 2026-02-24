from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .http_client import build_session
from .models import Deal

MAX_DISCORD_CONTENT_CHARS = 2000


def _reason_line(deal: Deal) -> Optional[str]:
    if deal.reason:
        return f"Why this deal: {deal.reason}"
    return None


def build_embed(deal: Deal, embed_color: int) -> Dict[str, Any]:
    steam_url = deal.steam_url
    main_url = steam_url or deal.deal_url

    price_line = f"**${deal.sale_price:.2f}** ~~${deal.normal_price:.2f}~~  (**-{deal.savings_pct:.0f}%**)"
    store_line = f"Store: **{deal.store_name}**"

    desc_lines = [price_line, store_line]
    if deal.coop_tags:
        desc_lines.append(f"Co-op: **{', '.join(deal.coop_tags)}**")

    if deal.review_summary:
        if deal.review_percent is not None and deal.review_count is not None:
            desc_lines.append(
                f"Steam Reviews: **{deal.review_summary}** ({deal.review_percent}% of {deal.review_count:,})"
            )
        else:
            desc_lines.append(f"Steam Reviews: **{deal.review_summary}**")

    reason_line = _reason_line(deal)
    if reason_line:
        desc_lines.append(reason_line)

    links_value = f"[Buy deal]({deal.deal_url})"
    if steam_url:
        links_value += f" • [Steam]({steam_url})"

    embed: Dict[str, Any] = {
        "title": deal.title[:256],
        "url": main_url,
        "description": "\n".join(desc_lines)[:4096],
        "color": embed_color,
        "fields": [{"name": "Links", "value": links_value, "inline": False}],
        "footer": {"text": f"Source: {deal.source_label} • Curated Co-op Deals"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if deal.thumb:
        embed["thumbnail"] = {"url": deal.thumb}
    elif deal.store_icon:
        embed["thumbnail"] = {"url": deal.store_icon}

    return embed


def _compose_content(message_title: str, metrics_summary: Optional[str]) -> str:
    title = message_title[:MAX_DISCORD_CONTENT_CHARS]
    if not metrics_summary:
        return title

    separator = "\n"
    room_for_metrics = MAX_DISCORD_CONTENT_CHARS - len(title) - len(separator)
    if room_for_metrics <= 0:
        return title

    trimmed_metrics = metrics_summary[:room_for_metrics]
    return f"{title}{separator}{trimmed_metrics}"


def post_embeds(
    webhook_url: str,
    username: str,
    content: str,
    embeds: List[Dict[str, Any]],
    role_id_to_ping: Optional[str] = None,
    timeout: int = 20,
) -> None:
    mention = f"<@&{role_id_to_ping}> " if role_id_to_ping else ""
    payload = {
        "content": f"{mention}{content}",
        "username": username,
        "embeds": embeds[:10],
        "allowed_mentions": {
            "parse": [],
            "roles": [role_id_to_ping] if role_id_to_ping else [],
        },
    }

    session = build_session()
    r = session.post(webhook_url, json=payload, timeout=timeout)
    r.raise_for_status()


def post_deals(
    webhook_url: str,
    username: str,
    deals: List[Deal],
    embed_color: int,
    message_title: str,
    role_id_to_ping: Optional[str] = None,
    metrics_summary: Optional[str] = None,
) -> None:
    embeds = [build_embed(d, embed_color) for d in deals]
    post_embeds(
        webhook_url=webhook_url,
        username=username,
        content=_compose_content(message_title, metrics_summary),
        embeds=embeds,
        role_id_to_ping=role_id_to_ping,
    )
