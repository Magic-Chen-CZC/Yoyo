from yoyo.db.models.guide import GuideGenerationJob
from yoyo.db.models.itinerary import ItineraryVersion
from yoyo.db.runtime import new_session
from yoyo.modules.guide.runtime import mark_job_failed, mark_job_running, mark_job_succeeded


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
            result = {
                "summary": version.plan_json.get("summary"),
                "stop_count": len(stops),
                "stops": [stop.get("name") for stop in stops],
                "guide_script": {
                    "title": version.plan_json.get("summary"),
                    "intro": (
                        f"This route starts with {stops[0].get('name')} and includes {len(stops)} stop(s)."
                        if stops else "This route has no planned stops yet."
                    ),
                },
                "card": {
                    "headline": version.plan_json.get("summary"),
                    "highlights": [stop.get("name") for stop in stops[:3]],
                },
                "audio": {
                    "status": "not_generated",
                    "url": None,
                },
            }
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
