from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE


def test_mock_seed_attractions_include_multiple_guide_segments() -> None:
    assert len(MOCK_SEED_BUNDLE.attractions) > 0
    first = MOCK_SEED_BUNDLE.attractions[0]
    assert len(first.guide_segments) >= 10
    assert any("overview" in segment.lower() or "historical" in segment.lower() for segment in first.guide_segments)
