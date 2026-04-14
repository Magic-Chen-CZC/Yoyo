from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

REPORT_DIR = Path("tests/reports")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live black-box stress against the running A APIs."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Running app base URL.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=20,
        help="How many black-box runs to execute.",
    )
    parser.add_argument("--concurrency", type=int, default=5, help="Parallel workers.")
    return parser.parse_args()


async def run_single_flow(client: httpx.AsyncClient, *, run_index: int) -> dict:
    started = time.perf_counter()
    failure_reason = None
    try:
        itinerary_response = await client.post(
            "/api/v1/planning/itineraries",
            json={
                "user_id": f"live-user-{run_index}",
                "title": f"live-blackbox-{run_index}",
                "preferences": {"preferred_poi_count": 2},
            },
        )
        itinerary_response.raise_for_status()
        itinerary = itinerary_response.json()["data"]

        session_response = await client.post(
            "/api/v1/session/guide",
            json={
                "itinerary_id": itinerary["id"],
                "itinerary_version_id": itinerary["version"]["id"],
                "context": {},
            },
        )
        session_response.raise_for_status()
        guide_session_id = session_response.json()["data"]["id"]

        current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
        current_response.raise_for_status()
        current = current_response.json()["data"]
        if current["current_stop"]["id"] != "stop-tiananmen-square":
            raise AssertionError("unexpected initial current_stop")

        map_response = await client.get(f"/api/v1/map/session/{guide_session_id}")
        map_response.raise_for_status()
        map_data = map_response.json()["data"]
        if map_data["current_stop"]["id"] != "stop-tiananmen-square":
            raise AssertionError("map current_stop mismatch")

        gps_far = await client.post(
            f"/api/v1/gps/update/{guide_session_id}",
            json={"latitude": 39.9042, "longitude": 116.4074},
        )
        gps_far.raise_for_status()
        if gps_far.json()["data"]["arrived"] is not False:
            raise AssertionError("far gps should not arrive")

        gps_near = await client.post(
            f"/api/v1/gps/update/{guide_session_id}",
            json={"latitude": 39.9050, "longitude": 116.3976},
        )
        gps_near.raise_for_status()
        if gps_near.json()["data"]["arrived"] is not True:
            raise AssertionError("near gps should arrive")

        play_response = await client.post(
            f"/api/v1/guide/playback/{guide_session_id}",
            json={"action": "play"},
        )
        play_response.raise_for_status()
        if play_response.json()["data"]["playback_state"] != "playing":
            raise AssertionError("playback should be playing")

        complete_response = await client.post(
            f"/api/v1/guide/playback/{guide_session_id}",
            json={"action": "complete"},
        )
        complete_response.raise_for_status()
        if complete_response.json()["data"]["playback_state"] != "not_triggered":
            raise AssertionError("playback should reset after complete")

        current_after = await client.get(f"/api/v1/session/{guide_session_id}/current")
        current_after.raise_for_status()
        current_after_data = current_after.json()["data"]
        if current_after_data["current_stop"]["id"] != "stop-forbidden-city":
            raise AssertionError("current stop should advance after complete")

        edit_response = await client.post(
            f"/api/v1/planning/itineraries/{itinerary['id']}/edits",
            json={
                "operation": "replace_stop",
                "target_stop_id": "stop-forbidden-city",
                "replacement_stop_name": "Jingshan Park",
            },
        )
        edit_response.raise_for_status()
        edited = edit_response.json()["data"]

        final_current = await client.get(f"/api/v1/session/{guide_session_id}/current")
        final_map = await client.get(f"/api/v1/map/session/{guide_session_id}")
        final_current.raise_for_status()
        final_map.raise_for_status()
        final_current_data = final_current.json()["data"]
        final_map_data = final_map.json()["data"]
        if final_current_data["itinerary_version_id"] != edited["version"]["id"]:
            raise AssertionError("session did not switch to edited version")
        if final_current_data["current_stop"]["id"] != "stop-jingshan-park":
            raise AssertionError("edited stop was not reflected in session current")
        if final_map_data["current_stop"]["id"] != "stop-jingshan-park":
            raise AssertionError("edited stop was not reflected in map")

        status = "passed"
    except Exception as error:  # noqa: BLE001
        status = "failed"
        failure_reason = str(error)

    return {
        "run_index": run_index,
        "status": status,
        "duration_seconds": time.perf_counter() - started,
        "failure_reason": failure_reason,
    }


async def execute_runs(*, base_url: str, repeat: int, concurrency: int) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        health = await client.get("/api/v1/health")
        health.raise_for_status()

        async def guarded(run_index: int) -> dict:
            async with semaphore:
                return await run_single_flow(client, run_index=run_index)

        tasks = [asyncio.create_task(guarded(run_index)) for run_index in range(1, repeat + 1)]
        return await asyncio.gather(*tasks)


def build_reports(
    *,
    base_url: str,
    repeat: int,
    concurrency: int,
    started_at: str,
    finished_at: str,
    wall_time_seconds: float,
    results: list[dict],
) -> tuple[dict, str]:
    durations = [result["duration_seconds"] for result in results]
    passed_runs = sum(result["status"] == "passed" for result in results)
    failed_runs = len(results) - passed_runs
    report = {
        "mode": "live_blackbox_stress",
        "base_url": base_url,
        "repeat": repeat,
        "concurrency": concurrency,
        "started_at": started_at,
        "finished_at": finished_at,
        "wall_time_seconds": round(wall_time_seconds, 6),
        "summary": {
            "total_runs": len(results),
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "average_duration_seconds": round(statistics.mean(durations), 6),
            "fastest_duration_seconds": round(min(durations), 6),
            "slowest_duration_seconds": round(max(durations), 6),
        },
        "runs": results,
        "failures": [result for result in results if result["status"] == "failed"],
    }

    lines = [
        "# A Live Black-box Stress Report",
        "",
        f"- Base URL: `{base_url}`",
        f"- Repeat: `{repeat}`",
        f"- Concurrency: `{concurrency}`",
        f"- Started at: `{started_at}`",
        f"- Finished at: `{finished_at}`",
        f"- Wall time: `{wall_time_seconds:.3f}s`",
        f"- Passed runs: `{passed_runs}`",
        f"- Failed runs: `{failed_runs}`",
        "",
        "| Run | Status | Duration (s) | Failure |",
        "| --- | --- | ---: | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result['run_index']} | {result['status']} | "
            f"{result['duration_seconds']:.3f} | {result['failure_reason'] or ''} |"
        )
    return report, "\n".join(lines) + "\n"


async def async_main() -> int:
    args = parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = REPORT_DIR / f"a_live_blackbox_stress_{timestamp}.json"
    markdown_path = REPORT_DIR / f"a_live_blackbox_stress_{timestamp}.md"

    started = datetime.now(UTC)
    perf_started = time.perf_counter()
    results = await execute_runs(
        base_url=args.base_url,
        repeat=max(args.repeat, 1),
        concurrency=max(args.concurrency, 1),
    )
    perf_finished = time.perf_counter()
    finished = datetime.now(UTC)

    report, markdown = build_reports(
        base_url=args.base_url,
        repeat=max(args.repeat, 1),
        concurrency=max(args.concurrency, 1),
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        wall_time_seconds=perf_finished - perf_started,
        results=results,
    )
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")

    print("A live black-box stress finished")
    print(
        f"Runs: {report['summary']['total_runs']} | Passed: {report['summary']['passed_runs']} | "
        f"Failed: {report['summary']['failed_runs']} | "
        f"Wall time: {report['wall_time_seconds']:.3f}s"
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    if report["failures"]:
        print("Failures:")
        for failure in report["failures"]:
            print(
                f"- run={failure['run_index']} | {failure['duration_seconds']:.3f}s | "
                f"{failure['failure_reason']}"
            )
    return 0 if report["summary"]["failed_runs"] == 0 else 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
