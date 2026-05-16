from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from yoyo.modules.knowledge.navigation_retriever import get_navigation_context
from yoyo.modules.knowledge.schemas import NavigationSlotPayload
from yoyo.modules.qa.formatters import format_navigation_text_answer


SMOKE_CASES = [
    {
        "case_id": "NVT-SMOKE-001",
        "query": "从北海公园走到恭王府，给我能照着走的文字路线。",
        "origin": "北海公园",
        "destinations": ["恭王府"],
    },
    {
        "case_id": "NVT-SMOKE-002",
        "query": "雍和宫出来以后步行去孔庙和国子监博物馆怎么走？",
        "origin": "雍和宫",
        "destinations": ["孔庙和国子监博物馆"],
    },
    {
        "case_id": "NVT-SMOKE-003",
        "query": "天坛到前门这段不要坐车，只说步行方向和每段距离。",
        "origin": "天坛",
        "destinations": ["前门"],
    },
    {
        "case_id": "NVT-SMOKE-004",
        "query": "从什刹海去南锣鼓巷，给我逐段步行路线。",
        "origin": "什刹海",
        "destinations": ["南锣鼓巷"],
    },
    {
        "case_id": "NVT-SMOKE-005",
        "query": "从中国国家博物馆步行到正阳门，路口和转向都说清楚。",
        "origin": "中国国家博物馆",
        "destinations": ["正阳门"],
    },
    {
        "case_id": "NVT-SMOKE-006",
        "query": "鸟巢到水立方走路过去怎么走？",
        "origin": "鸟巢",
        "destinations": ["水立方"],
    },
    {
        "case_id": "NVT-SMOKE-007",
        "query": "从798艺术区走到将台地铁站，给我文字导航。",
        "origin": "798艺术区",
        "destinations": ["将台地铁站"],
    },
    {
        "case_id": "NVT-SMOKE-008",
        "query": "北京动物园到五塔寺步行怎么走？每一段加上大概米数。",
        "origin": "北京动物园",
        "destinations": ["五塔寺"],
    },
]


async def run_case(case: dict[str, object]) -> dict[str, object]:
    started = time.perf_counter()
    slot_payload = NavigationSlotPayload(
        origin=str(case["origin"]),
        destinations=list(case["destinations"]),
        mode="walking",
        mode_source="explicit",
        source="rule",
        request_kind="multi_leg" if len(case["destinations"]) > 1 else "explicit_route",
    )
    context = await get_navigation_context(slot_result=slot_payload)
    answer = format_navigation_text_answer(
        context.origin_name,
        context.destination_name,
        context.steps,
        context.distance_meters,
        context.duration_seconds,
        legs=context.legs,
        degraded_reason=context.reason if context.status != "available" else None,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    step_dicts = [step.model_dump() for step in context.steps]
    turn_steps = [step for step in step_dicts if step.get("turn_location_text")]
    return {
        "case_id": case["case_id"],
        "query": case["query"],
        "origin": case["origin"],
        "destinations": case["destinations"],
        "status": context.status,
        "reason": context.reason,
        "distance_meters": context.distance_meters,
        "duration_seconds": context.duration_seconds,
        "leg_count": len(context.legs),
        "step_count": len(context.steps),
        "turn_location_hit_count": len(turn_steps),
        "first_turn_locations": [str(step.get("turn_location_text")) for step in turn_steps[:4]],
        "latency_ms": latency_ms,
        "answer": answer,
        "steps": step_dicts,
    }


def print_table(results: list[dict[str, object]]) -> None:
    headers = ["case_id", "status", "distance_m", "steps", "turn_hits", "latency_ms", "answer_preview"]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    for result in results:
        answer = str(result.get("answer") or "").replace("\n", " ")
        preview = answer[:120] + ("..." if len(answer) > 120 else "")
        row = [
            str(result.get("case_id")),
            str(result.get("status")),
            str(result.get("distance_meters")),
            str(result.get("step_count")),
            str(result.get("turn_location_hit_count")),
            str(result.get("latency_ms")),
            preview,
        ]
        print("| " + " | ".join(cell.replace("|", "/") for cell in row) + " |")


async def main() -> None:
    results = []
    for case in SMOKE_CASES:
        results.append(await run_case(case))
        await asyncio.sleep(0.2)

    output_path = Path("evals/results/navigation_turnpoint_smoke_20260516.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(results)
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
