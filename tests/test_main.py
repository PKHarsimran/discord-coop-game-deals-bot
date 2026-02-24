from bot.main import _franchise_key, _passes_review_threshold, _score_deal
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
