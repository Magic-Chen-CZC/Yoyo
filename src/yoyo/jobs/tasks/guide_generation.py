from yoyo.core.config import get_settings
from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import ItineraryVersion
from yoyo.modules.guide.content_builder import build_guide_bundle
from yoyo.modules.guide.generator import generate_guide_text_blocks
from yoyo.modules.knowledge.attraction_retriever import get_attraction_context
from yoyo.modules.knowledge.profile_retriever import get_profile_context
from yoyo.db.runtime import new_session
from yoyo.modules.guide.runtime import mark_job_failed, mark_job_running, mark_job_succeeded


# 这是后台 worker 真正执行的 guide 生成任务。
# 当前阶段改为 SQL-first：路线信息 + 用户画像 + 景点介绍字段共同生成 guide bundle。
async def run_guide_generation_job(ctx: dict, guide_generation_job_id: str) -> dict[str, object]:
    async with await new_session() as session:
        job = await session.get(GuideGenerationJob, guide_generation_job_id)
        if job is None:
            return {
                "guide_generation_job_id": guide_generation_job_id,
                "status": "missing",
            }

        await mark_job_running(session, job)

        try:
            version = await session.get(ItineraryVersion, job.itinerary_version_id)
            if version is None:
                raise ValueError("itinerary version not found")

            stops = version.plan_json.get("stops", [])
            planner_input = version.planner_input_json or {}
            profile = await get_profile_context(planner_input.get("user_id"), session=session)
            attractions = []
            for stop in stops:
                stop_name = stop.get("name")
                attraction = await get_attraction_context(stop_name if isinstance(stop_name, str) else None, session=session)
                if attraction is not None:
                    attractions.append(attraction)

            settings = get_settings()
            llm_bundle, llm_metadata = await generate_guide_text_blocks(
                provider=settings.llm_provider,
                model=settings.llm_model,
                summary=version.plan_json.get("summary"),
                attractions=attractions,
                profile=profile,
            )
            result = build_guide_bundle(
                summary=version.plan_json.get("summary"),
                attractions=attractions,
                profile=profile,
                llm_bundle=llm_bundle,
            )
            result["generation_metadata"] = llm_metadata
            await mark_job_succeeded(session, job, result)
            return {
                "guide_generation_job_id": guide_generation_job_id,
                "status": "succeeded",
                "result": result,
            }
        except Exception as error:
            await mark_job_failed(session, job, str(error))
            return {
                "guide_generation_job_id": guide_generation_job_id,
                "status": "failed",
                "error": str(error),
            }
