from bot.config import load_settings


def test_review_threshold_env_parsing(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com")
    monkeypatch.setenv("MIN_REVIEW_PERCENT", "85")
    monkeypatch.setenv("MIN_REVIEW_COUNT", "500")
    monkeypatch.setenv("PROFILE_NAME", "nightly")

    settings = load_settings()

    assert settings.min_review_percent == 85
    assert settings.min_review_count == 500
    assert settings.profile_name == "nightly"


def test_franchise_settings_bounds(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com")
    monkeypatch.setenv("FRANCHISE_DEDUPE_WORDS", "99")
    settings = load_settings()
    assert settings.franchise_dedupe_words == 5


def test_profile_name_is_normalized(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com")
    monkeypatch.setenv("PROFILE_NAME", "  Nightly / Deals!  ")
    settings = load_settings()
    assert settings.profile_name == "nightly-deals"


def test_profile_name_falls_back_to_default_when_empty_after_sanitize(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com")
    monkeypatch.setenv("PROFILE_NAME", "!!!___---")
    settings = load_settings()
    assert settings.profile_name == "default"


def test_profile_name_collapses_repeated_separators(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com")
    monkeypatch.setenv("PROFILE_NAME", "nightly___deals---us")
    settings = load_settings()
    assert settings.profile_name == "nightly-deals-us"
