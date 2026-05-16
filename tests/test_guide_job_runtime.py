# 这份测试聚焦后台任务 run_guide_generation_job。
# 重点是确认：job 状态会更新、result_json 结构符合预期。
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.jobs.tasks.guide_generation import run_guide_generation_job
from yoyo.modules.shared.enums import AssetStatus, GuideGenerationJobStatus, GuideGenerationJobType, ItineraryStatus, ItineraryVersionStatus


async def _create_runtime_guide_job(db_session: AsyncSession) -> GuideGenerationJob:
    itinerary = Itinerary(user_id="runtime-user", city_code="beijing", title="Runtime trip", status=ItineraryStatus.ACTIVE)
    db_session.add(itinerary)
    await db_session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json={"preferences": {"preferred_poi_count": 2}},
        plan_json={
            "summary": "Starter Beijing itinerary",
            "stops": [{"name": "Tiananmen Square"}, {"name": "Forbidden City"}],
        },
        status=ItineraryVersionStatus.ACTIVE,
        created_by="test",
    )
    db_session.add(version)
    await db_session.flush()

    itinerary.current_version_id = version.id

    job = GuideGenerationJob(
        itinerary_version_id=version.id,
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json={"itinerary_id": itinerary.id, "itinerary_version_id": version.id},
    )
    db_session.add(job)
    await db_session.commit()
    return job


@pytest.mark.asyncio
async def test_run_guide_generation_job_updates_job(db_session: AsyncSession, monkeypatch) -> None:
    job = await _create_runtime_guide_job(db_session)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"intro":"Tiananmen Square opens this route with a clear historical frame.","outro":"This finishes the route with a compact takeaway.","card_headline":"Historic Beijing Walk","card_highlights":["Tiananmen Square","Forbidden City"],"card_practical_tips":["Start early"],"stop_scripts":[{"stop_name":"Tiananmen Square","narration":"Tiananmen Square is the ceremonial opening of the route.","why_it_matters":"It anchors the political symbolism of modern Beijing.","visitor_tip":"Pause for the broad north-south axis."},{"stop_name":"Forbidden City","narration":"The Forbidden City expands the imperial story.","why_it_matters":"It shows how imperial power was spatially organized.","visitor_tip":"Budget extra time for the main halls."}]}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "succeeded"

    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == GuideGenerationJobStatus.SUCCEEDED
    assert persisted_job.asset_status == AssetStatus.READY
    result_json = persisted_job.result_json
    assert result_json is not None
    assert result_json["summary"] == "Starter Beijing itinerary"
    assert result_json["stop_count"] == 2
    assert result_json["stops"] == ["Tiananmen Square", "Forbidden City"]
    assert result_json["guide_script"]["title"] == "Starter Beijing itinerary"
    assert result_json["guide_script"]["intro"] == "Tiananmen Square opens this route with a clear historical frame."
    assert len(result_json["guide_script"]["stops"]) == 2
    assert result_json["guide_script"]["stops"][0]["guide_segments"]
    assert result_json["guide_script"]["stops"][0]["segment_count"] >= 10
    assert result_json["guide_script"]["stops"][0]["more_content_available"] is True
    assert result_json["card"]["headline"] == "Historic Beijing Walk"
    assert result_json["audio"]["status"] in {"pending", "unavailable"}
    assert isinstance(result_json["audio"]["voice"], str)
    assert result_json["audio"]["voice"]
    assert result_json["generation_metadata"]["profile_user_id"] is None
    assert result_json["generation_metadata"]["llm"]["structured_output_valid"] is True
    assert result_json["generation_metadata"]["llm"]["structured_output_type"] == "guide_bundle"


@pytest.mark.asyncio
async def test_run_guide_generation_job_marks_failed_when_version_is_missing(db_session: AsyncSession, monkeypatch) -> None:
    job = GuideGenerationJob(
        itinerary_version_id="missing-version",
        job_type=GuideGenerationJobType.GUIDE_BUNDLE,
        status=GuideGenerationJobStatus.QUEUED,
        asset_status=AssetStatus.PENDING,
        payload_json={"itinerary_id": "missing-itinerary", "itinerary_version_id": "missing-version"},
    )
    db_session.add(job)
    await db_session.commit()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "failed"
    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == GuideGenerationJobStatus.FAILED
    assert persisted_job.asset_status == AssetStatus.FAILED
    assert persisted_job.error_message == "itinerary version not found"


@pytest.mark.asyncio
async def test_run_guide_generation_job_accepts_clean_fenced_json_bundle(db_session: AsyncSession, monkeypatch) -> None:
    job = await _create_runtime_guide_job(db_session)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '```json\n{"intro":"Tiananmen Square opens this route with a clear historical frame.","outro":"This finishes the route with a compact takeaway.","card_headline":"Historic Beijing Walk","card_highlights":["Tiananmen Square","Forbidden City"],"card_practical_tips":["Start early"],"stop_scripts":[{"stop_name":"Tiananmen Square","narration":"Tiananmen Square is the ceremonial opening of the route.","why_it_matters":"It anchors the political symbolism of modern Beijing.","visitor_tip":"Pause for the broad north-south axis."},{"stop_name":"Forbidden City","narration":"The Forbidden City expands the imperial story.","why_it_matters":"It shows how imperial power was spatially organized.","visitor_tip":"Budget extra time for the main halls."}]}\n```'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "succeeded"
    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    result_json = persisted_job.result_json
    assert result_json is not None
    assert result_json["guide_script"]["intro"] == "Tiananmen Square opens this route with a clear historical frame."
    assert "Narrative tone" not in result_json["guide_script"]["intro"]
    assert "keep a" not in result_json["guide_script"]["outro"].lower() or "guide_style" not in result_json["guide_script"]["outro"].lower()
    assert result_json["generation_metadata"]["llm"]["structured_output_valid"] is True


@pytest.mark.asyncio
async def test_run_guide_generation_job_falls_back_when_runtime_returns_error(db_session: AsyncSession, monkeypatch) -> None:
    job = await _create_runtime_guide_job(db_session)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = type("Error", (), {"model_dump": lambda self: {"error_type": "provider_error", "message": "boom", "retryable": False}})()

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "succeeded"
    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == GuideGenerationJobStatus.SUCCEEDED
    assert persisted_job.asset_status == AssetStatus.READY
    result_json = persisted_job.result_json
    assert result_json is not None
    assert result_json["guide_script"]["title"] == "Starter Beijing itinerary"
    assert result_json["generation_metadata"]["llm"]["fallback_used"] is True


@pytest.mark.asyncio
async def test_run_guide_generation_job_falls_back_when_llm_bundle_is_structurally_invalid(db_session: AsyncSession, monkeypatch) -> None:
    job = await _create_runtime_guide_job(db_session)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"intro":"Guide intro only","outro":"Guide outro only","card_headline":"Bad bundle","card_highlights":["One"],"card_practical_tips":["Tip"],"stop_scripts":[{"stop_name":"Tiananmen Square","narration":"","why_it_matters":"Important"}]}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "succeeded"

    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == GuideGenerationJobStatus.SUCCEEDED
    assert persisted_job.asset_status == AssetStatus.READY
    result_json = persisted_job.result_json
    assert result_json is not None
    assert result_json["guide_script"]["title"] == "Starter Beijing itinerary"
    assert len(result_json["guide_script"]["stops"]) == 2
    assert result_json["guide_script"]["stops"][0]["guide_segments"]
    assert result_json["card"]["headline"] == "Starter Beijing itinerary"
    assert "Narrative tone" not in result_json["guide_script"]["intro"]
    assert "keep the pacing comfortable" not in result_json["guide_script"]["stops"][0]["visitor_tip"].lower()
    assert result_json["generation_metadata"]["llm"]["structured_output_valid"] is False
    assert result_json["generation_metadata"]["llm"]["structured_output_type"] == "guide_bundle"


@pytest.mark.asyncio
async def test_run_guide_generation_job_sanitizes_wrapper_noise_in_bundle_text(db_session: AsyncSession, monkeypatch) -> None:
    job = await _create_runtime_guide_job(db_session)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"intro":"Answer: Tiananmen Square opens this route with a clear historical frame.","outro":"Here is your answer: This finishes the route with a compact takeaway.","card_headline":"Answer: Historic Beijing Walk","card_highlights":["Answer: Tiananmen Square","Forbidden City"],"card_practical_tips":["Answer: Start early"],"stop_scripts":[{"stop_name":"Tiananmen Square","narration":"Answer: Tiananmen Square is the ceremonial opening of the route.","why_it_matters":"Here is your answer: It anchors the political symbolism of modern Beijing.","visitor_tip":"Answer: Pause for the broad north-south axis."},{"stop_name":"Forbidden City","narration":"The Forbidden City expands the imperial story.","why_it_matters":"It shows how imperial power was spatially organized.","visitor_tip":"Budget extra time for the main halls."}]}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_new_session() -> AsyncSession:
        return db_session

    monkeypatch.setattr("yoyo.jobs.tasks.guide_generation.new_session", fake_new_session)
    monkeypatch.setattr("yoyo.modules.guide.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await run_guide_generation_job({}, job.id)

    assert result["status"] == "succeeded"
    persisted_job = await db_session.get(GuideGenerationJob, job.id)
    assert persisted_job is not None
    result_json = persisted_job.result_json
    assert result_json is not None
    assert result_json["guide_script"]["intro"] == "Tiananmen Square opens this route with a clear historical frame."
    assert result_json["guide_script"]["outro"] == "This finishes the route with a compact takeaway."
    assert result_json["card"]["headline"] == "Historic Beijing Walk"
    assert result_json["card"]["highlights"][0] == "Tiananmen Square"
    assert result_json["card"]["practical_tips"][0] == "Start early"
    assert result_json["guide_script"]["stops"][0]["narration"] == "Tiananmen Square is the ceremonial opening of the route."
    assert result_json["guide_script"]["stops"][0]["why_it_matters"] == "It anchors the political symbolism of modern Beijing."
    assert result_json["guide_script"]["stops"][0]["visitor_tip"] == "Pause for the broad north-south axis."
