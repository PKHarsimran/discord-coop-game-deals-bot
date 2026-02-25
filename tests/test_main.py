import requests
from bot.main import (
    RunMetrics,
    _build_metrics_summary,
    _fetch_optional_popularity_stats,
    _franchise_key,
    _passes_review_threshold,
    _score_deal,
)
from bot.models import Deal


def _deal(**kwargs):
    base = dict(
        deal_id="1",
        title="Deep Rock Galactic",
        sale_price=4.99,
        normal_price=29.99,
        savings_pct=80.0,
        store_id="1",
        store_name="Steam",
        store_icon=None,
        steam_app_id="123",
        thumb=None,
    )
    base.update(kwargs)
    return Deal(**base)


def test_score_prefers_better_reviews_and_discount():
    a = _deal(review_percent=90, coop_tags=["Co-op", "Online Co-op"])
    b = _deal(review_percent=60, savings_pct=50.0, coop_tags=["Co-op"])
    assert _score_deal(a, sweet_spot=5.0, was_posted=False) > _score_deal(b, sweet_spot=5.0, was_posted=False)


def test_franchise_key_normalization():
    assert _franchise_key("Warhammer 40,000: Darktide", 2) == "warhammer 40"
    assert _franchise_key("Portal 2 - DLC Pack", 2) == "portal 2"


def test_review_threshold_requires_known_reviews_when_enabled():
    assert _passes_review_threshold(90, 1000, 70, 100)
    assert not _passes_review_threshold(None, None, 70, 100)
    assert not _passes_review_threshold(65, 1000, 70, 100)
    assert _passes_review_threshold(None, None, 0, 0)


def test_fetch_optional_popularity_stats_returns_none_when_apis_fail(monkeypatch):
    def _boom(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr("bot.main.fetch_current_players", _boom)
    monkeypatch.setattr("bot.main.fetch_steamspy_stats", _boom)

    assert _fetch_optional_popularity_stats("570") == (None, None, None)


def test_build_metrics_summary_is_detailed_and_readable():
    metrics = RunMetrics(
        fetched_total=42,
        filtered_price=5,
        filtered_discount=3,
        filtered_keyword=1,
        filtered_missing_appid=2,
        filtered_non_coop=8,
        filtered_reviews=4,
        filtered_already_posted=6,
        filtered_duplicate_appid=2,
        filtered_duplicate_franchise=1,
        metadata_errors=1,
        posted_count=10,
        source_counts={"cheapshark": 30, "steam_direct": 12},
    )

    summary = _build_metrics_summary(metrics)
    assert "📊 Deal run summary" in summary
    assert "Fetched: 42 (CheapShark: 30, Steam Direct: 12)" in summary
    assert "Posted: 10" in summary
    assert "metadata errors".lower() in summary.lower()
