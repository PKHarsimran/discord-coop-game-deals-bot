from bot.discord_webhook import _compose_content, MAX_DISCORD_CONTENT_CHARS, build_embed
from bot.models import Deal


def test_compose_content_includes_metrics_when_present():
    content = _compose_content("Title", "Fetched: 10 | Posted: 3")
    assert "Title" in content
    assert "Fetched: 10" in content


def test_compose_content_truncates_to_discord_limit():
    long_title = "T" * (MAX_DISCORD_CONTENT_CHARS + 100)
    content = _compose_content(long_title, None)
    assert len(content) == MAX_DISCORD_CONTENT_CHARS


def test_compose_content_preserves_title_and_trims_metrics_first():
    title = "Daily digest"
    metrics = "M" * (MAX_DISCORD_CONTENT_CHARS * 2)
    content = _compose_content(title, metrics)
    assert content.startswith("Daily digest\n")
    assert len(content) == MAX_DISCORD_CONTENT_CHARS


def test_compose_content_ignores_metrics_when_title_already_at_limit():
    title = "T" * MAX_DISCORD_CONTENT_CHARS
    content = _compose_content(title, "Fetched: 1")
    assert content == title


def _deal(**kwargs):
    base = dict(
        deal_id="1",
        title="Lethal Company",
        sale_price=7.99,
        normal_price=9.99,
        savings_pct=20.0,
        store_id="1",
        store_name="Steam",
        store_icon=None,
        steam_app_id="1966720",
        thumb=None,
        source_label="CheapShark",
    )
    base.update(kwargs)
    return Deal(**base)


def test_build_embed_includes_steamdb_link_and_stats():
    deal = _deal(current_players=12345, steamspy_ccu=22000, steamspy_owners="1,000,000 .. 2,000,000")
    embed = build_embed(deal, embed_color=123)
    assert "[SteamDB](https://steamdb.info/app/1966720/)" in embed["fields"][0]["value"]
    assert "SteamDB-ish stats" in embed["description"]
    assert "Players now: **12,345**" in embed["description"]
    assert "Owners est.: **1,000,000 .. 2,000,000**" in embed["description"]
