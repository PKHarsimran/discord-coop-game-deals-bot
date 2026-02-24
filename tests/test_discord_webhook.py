from bot.discord_webhook import _compose_content, MAX_DISCORD_CONTENT_CHARS


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
