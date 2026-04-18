import pytest

from yoyo.modules.knowledge.attraction_retriever import get_attraction_context
from yoyo.modules.knowledge.profile_retriever import get_profile_context
from yoyo.modules.knowledge.schemas import AttractionContext


@pytest.mark.asyncio
async def test_attraction_context_uses_mock_fallback_in_test_env() -> None:
    attraction = await get_attraction_context("Tiananmen Square", session=None)
    assert attraction is not None
    assert attraction.source == "mock_postgres"


@pytest.mark.asyncio
async def test_profile_context_uses_mock_fallback_in_test_env() -> None:
    profile = await get_profile_context("mock-user-1", session=None)
    assert profile is not None
    assert profile.source == "mock_postgres"


@pytest.mark.asyncio
async def test_attraction_context_can_disable_mock_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "yoyo.modules.knowledge.attraction_retriever.allow_mock_knowledge_fallback",
        lambda: False,
    )
    attraction = await get_attraction_context("Tiananmen Square", session=None)
    assert attraction is None


@pytest.mark.asyncio
async def test_profile_context_can_disable_mock_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "yoyo.modules.knowledge.profile_retriever.allow_mock_profile_fallback",
        lambda: False,
    )
    profile = await get_profile_context("mock-user-1", session=None)
    assert profile is not None
    assert profile.user_id == "mock-user-1"
    assert profile.source == "derived_default"


@pytest.mark.asyncio
async def test_attraction_context_returns_none_for_missing_real_data_when_mock_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "yoyo.modules.knowledge.attraction_retriever.allow_mock_knowledge_fallback",
        lambda: False,
    )
    attraction = await get_attraction_context("Nonexistent Attraction", session=None)
    assert attraction is None


@pytest.mark.asyncio
async def test_profile_context_falls_back_to_derived_default_when_mock_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "yoyo.modules.knowledge.profile_retriever.allow_mock_profile_fallback",
        lambda: False,
    )
    profile = await get_profile_context("real-user-123", session=None)
    assert profile is not None
    assert profile.user_id == "real-user-123"
    assert profile.source == "derived_default"
