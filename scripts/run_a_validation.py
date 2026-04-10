from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

TEST_FILE = "tests/test_a_validation_suite.py"
REPORT_DIR = Path("tests/reports")
BLOCK_ORDER = [
    "A1_route_editing",
    "A2_session_runtime",
    "A3_gps_geofence",
    "A4_map_payload",
    "A5_contract_hygiene",
    "A_integration",
]
BLOCK_LABELS = {
    "test_a1_": "A1_route_editing",
    "test_a2_": "A2_session_runtime",
    "test_a3_": "A3_gps_geofence",
    "test_a4_": "A4_map_payload",
    "test_a5_": "A5_contract_hygiene",
    "test_a_integration_": "A_integration",
}


@dataclass
class TestCaseResult:
    node_id: str
    name: str
    block: str
    status: str
    duration_seconds: float
    failure_reason: str | None


@dataclass
class ValidationRun:
    run_index: int
    exit_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    command: list[str]
    results: list[TestCaseResult]
    stdout: str
    stderr: str
    junit_path: str


def infer_block(test_name: str) -> str:
    for prefix, block_name in BLOCK_LABELS.items():
        if test_name.startswith(prefix):
            return block_name
    return "unclassified"


def summarize_failure(node: ElementTree.Element) -> str:
    message = node.attrib.get("message", "").strip()
    text = (node.text or "").strip()
    candidate = message or text
    if not candidate:
        return "unknown failure"

    for line in candidate.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:300]

    return candidate[:300]


def parse_junit_xml(xml_path: Path) -> list[TestCaseResult]:
    root = ElementTree.parse(xml_path).getroot()
    results: list[TestCaseResult] = []

    for testcase in root.findall(".//testcase"):
        name = testcase.attrib.get("name", "")
        classname = testcase.attrib.get("classname", "")
        node_id = f"{classname}::{name}" if classname else name
        duration_seconds = float(testcase.attrib.get("time", 0.0))

        failure_node = testcase.find("failure")
        error_node = testcase.find("error")
        skipped_node = testcase.find("skipped")

        status = "passed"
        failure_reason = None
        detail_node = failure_node or error_node
        if detail_node is not None:
            status = "failed" if failure_node is not None else "error"
            failure_reason = summarize_failure(detail_node)
        elif skipped_node is not None:
            status = "skipped"
            failure_reason = skipped_node.attrib.get("message") or "skipped"

        results.append(
            TestCaseResult(
                node_id=node_id,
                name=name,
                block=infer_block(name),
                status=status,
                duration_seconds=duration_seconds,
                failure_reason=failure_reason,
            )
        )

    return results


def build_block_report(results: list[TestCaseResult]) -> list[dict]:
    block_buckets: dict[str, list[TestCaseResult]] = defaultdict(list)
    for result in results:
        block_buckets[result.block].append(result)

    blocks = []
    for block_name in BLOCK_ORDER:
        block_results = block_buckets.get(block_name, [])
        blocks.append(
            {
                "block": block_name,
                "total": len(block_results),
                "passed": sum(item.status == "passed" for item in block_results),
                "failed": sum(item.status in {"failed", "error"} for item in block_results),
                "skipped": sum(item.status == "skipped" for item in block_results),
                "duration_seconds": round(
                    sum(item.duration_seconds for item in block_results),
                    6,
                ),
                "tests": [asdict(item) for item in block_results],
            }
        )
    return blocks


def build_single_report(
    *,
    run: ValidationRun,
    report_paths: dict[str, str],
) -> dict:
    results = run.results
    passed = sum(result.status == "passed" for result in results)
    failed = sum(result.status in {"failed", "error"} for result in results)
    skipped = sum(result.status == "skipped" for result in results)
    failures = [
        {
            "block": result.block,
            "node_id": result.node_id,
            "duration_seconds": result.duration_seconds,
            "failure_reason": result.failure_reason,
        }
        for result in results
        if result.status in {"failed", "error"}
    ]
    return {
        "mode": "single",
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "duration_seconds": round(run.duration_seconds, 6),
        "command": run.command,
        "exit_code": run.exit_code,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "all_passed": failed == 0 and run.exit_code == 0,
        },
        "blocks": build_block_report(results),
        "failures": failures,
        "tests": [asdict(result) for result in results],
        "report_paths": report_paths,
        "pytest_stdout": run.stdout,
        "pytest_stderr": run.stderr,
    }


def build_stress_report(
    *,
    started_at: str,
    finished_at: str,
    wall_time_seconds: float,
    runs: list[ValidationRun],
    repeat: int,
    concurrency: int,
    report_paths: dict[str, str],
) -> dict:
    passed_runs = sum(run.exit_code == 0 for run in runs)
    failed_runs = len(runs) - passed_runs
    failures = []
    for run in runs:
        if run.exit_code == 0:
            continue
        failures.append(
            {
                "run_index": run.run_index,
                "duration_seconds": run.duration_seconds,
                "failure_reason": summarize_run_failure(run),
            }
        )

    return {
        "mode": "stress",
        "started_at": started_at,
        "finished_at": finished_at,
        "wall_time_seconds": round(wall_time_seconds, 6),
        "repeat": repeat,
        "concurrency": concurrency,
        "summary": {
            "total_runs": len(runs),
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "all_passed": failed_runs == 0,
            "average_duration_seconds": round(
                sum(run.duration_seconds for run in runs) / len(runs),
                6,
            ),
            "fastest_duration_seconds": round(min(run.duration_seconds for run in runs), 6),
            "slowest_duration_seconds": round(max(run.duration_seconds for run in runs), 6),
        },
        "runs": [
            {
                "run_index": run.run_index,
                "exit_code": run.exit_code,
                "duration_seconds": round(run.duration_seconds, 6),
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "failure_reason": summarize_run_failure(run) if run.exit_code != 0 else None,
                "blocks": build_block_report(run.results),
            }
            for run in runs
        ],
        "failures": failures,
        "report_paths": report_paths,
    }


def summarize_run_failure(run: ValidationRun) -> str:
    for result in run.results:
        if result.status in {"failed", "error"} and result.failure_reason:
            return f"{result.node_id}: {result.failure_reason}"
    stdout_line = next((line.strip() for line in run.stdout.splitlines() if line.strip()), "")
    stderr_line = next((line.strip() for line in run.stderr.splitlines() if line.strip()), "")
    return stdout_line or stderr_line or f"pytest exited with code {run.exit_code}"


def build_markdown_report(report: dict) -> str:
    if report["mode"] == "stress":
        return build_stress_markdown_report(report)
    return build_single_markdown_report(report)


def build_single_markdown_report(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# A Validation Report",
        "",
        "## Summary",
        f"- Started at: `{report['started_at']}`",
        f"- Finished at: `{report['finished_at']}`",
        f"- Total duration: `{report['duration_seconds']:.3f}s`",
        f"- Total tests: `{summary['total']}`",
        f"- Passed: `{summary['passed']}`",
        f"- Failed: `{summary['failed']}`",
        f"- Skipped: `{summary['skipped']}`",
        "",
        "## Block Results",
        "",
        "| Block | Total | Passed | Failed | Skipped | Duration (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for block in report["blocks"]:
        lines.append(
            f"| {block['block']} | {block['total']} | {block['passed']} | {block['failed']} | "
            f"{block['skipped']} | {block['duration_seconds']:.3f} |"
        )

    lines.extend(["", "## Test Cases", ""])
    for block in report["blocks"]:
        lines.append(f"### {block['block']}")
        if not block["tests"]:
            lines.append("- No tests collected")
            lines.append("")
            continue

        for test in block["tests"]:
            line = f"- `{test['name']}`: `{test['status']}` in `{test['duration_seconds']:.3f}s`"
            if test["failure_reason"]:
                line += f" - {test['failure_reason']}"
            lines.append(line)
        lines.append("")

    lines.extend(["## Failures", ""])
    if not report["failures"]:
        lines.append("- None")
    else:
        for failure in report["failures"]:
            lines.append(
                f"- `{failure['block']}` `{failure['node_id']}` failed in "
                f"`{failure['duration_seconds']:.3f}s`: {failure['failure_reason']}"
            )

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                f"- A 五个块分别验证完成；当前总通过 `{summary['passed']}/{summary['total']}`，"
                f"失败 `{summary['failed']}`。"
            ),
            (
                "- 串联链路是否跑通以 `A_integration` 块为准；若该块有失败，优先查看 "
                "Failures 部分中的失败原因。"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def build_stress_markdown_report(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# A Validation Stress Report",
        "",
        "## Summary",
        f"- Started at: `{report['started_at']}`",
        f"- Finished at: `{report['finished_at']}`",
        f"- Repeat: `{report['repeat']}`",
        f"- Concurrency: `{report['concurrency']}`",
        f"- Wall time: `{report['wall_time_seconds']:.3f}s`",
        f"- Passed runs: `{summary['passed_runs']}`",
        f"- Failed runs: `{summary['failed_runs']}`",
        f"- Average run duration: `{summary['average_duration_seconds']:.3f}s`",
        f"- Fastest run: `{summary['fastest_duration_seconds']:.3f}s`",
        f"- Slowest run: `{summary['slowest_duration_seconds']:.3f}s`",
        "",
        "## Runs",
        "",
        "| Run | Status | Duration (s) | Failure |",
        "| --- | --- | ---: | --- |",
    ]

    for run in report["runs"]:
        status = "passed" if run["exit_code"] == 0 else "failed"
        failure_reason = run["failure_reason"] or ""
        lines.append(
            f"| {run['run_index']} | {status} | {run['duration_seconds']:.3f} | {failure_reason} |"
        )

    lines.extend(["", "## Conclusion", ""])
    lines.append(
        f"- 压测共运行 `{summary['total_runs']}` 轮，跑通 `{summary['passed_runs']}`，"
        f"失败 `{summary['failed_runs']}`。"
    )
    if report["failures"]:
        lines.append("- 失败轮次详见上表与 JSON 报告。")
    else:
        lines.append("- 本轮 stress 没有观察到 flaky 失败。")
    return "\n".join(lines) + "\n"


def print_terminal_summary(report: dict) -> None:
    if report["mode"] == "stress":
        summary = report["summary"]
        print("A validation stress finished")
        print(
            f"Runs: {summary['total_runs']} | Passed: {summary['passed_runs']} | "
            f"Failed: {summary['failed_runs']} | Wall time: {report['wall_time_seconds']:.3f}s | "
            f"Avg/run: {summary['average_duration_seconds']:.3f}s"
        )
        print("")
        if report["failures"]:
            print("Failures:")
            for failure in report["failures"]:
                print(
                    f"- run={failure['run_index']} | {failure['duration_seconds']:.3f}s | "
                    f"{failure['failure_reason']}"
                )
        else:
            print("Failures: none")
        print("")
        print(f"JSON report: {report['report_paths']['json']}")
        print(f"Markdown report: {report['report_paths']['markdown']}")
        return

    summary = report["summary"]
    print("A validation finished")
    print(
        f"Total: {summary['total']} | Passed: {summary['passed']} | "
        f"Failed: {summary['failed']} | Skipped: {summary['skipped']} | "
        f"Duration: {report['duration_seconds']:.3f}s"
    )
    print("")
    for block in report["blocks"]:
        print(
            f"{block['block']}: total={block['total']} passed={block['passed']} "
            f"failed={block['failed']} skipped={block['skipped']} "
            f"duration={block['duration_seconds']:.3f}s"
        )

    if report["failures"]:
        print("")
        print("Failures:")
        for failure in report["failures"]:
            print(
                f"- {failure['block']} | {failure['node_id']} | "
                f"{failure['duration_seconds']:.3f}s | {failure['failure_reason']}"
            )

    print("")
    print(f"JSON report: {report['report_paths']['json']}")
    print(f"Markdown report: {report['report_paths']['markdown']}")


def run_validation_once(*, run_index: int, timestamp: str) -> ValidationRun:
    junit_path = REPORT_DIR / f"a_validation_{timestamp}_run{run_index:03d}.xml"
    command = [
        sys.executable,
        "-m",
        "pytest",
        TEST_FILE,
        "-q",
        "-vv",
        "--durations=0",
        f"--junit-xml={junit_path}",
    ]

    started = datetime.now(UTC)
    perf_started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    perf_finished = time.perf_counter()
    finished = datetime.now(UTC)

    results = parse_junit_xml(junit_path) if junit_path.exists() else []
    return ValidationRun(
        run_index=run_index,
        exit_code=completed.returncode,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=perf_finished - perf_started,
        command=command,
        results=results,
        stdout=completed.stdout,
        stderr=completed.stderr,
        junit_path=str(junit_path),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A validation suite and build reports.")
    parser.add_argument("--repeat", type=int, default=1, help="How many times to run the suite.")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="How many suite runs to execute in parallel.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repeat = max(args.repeat, 1)
    concurrency = max(args.concurrency, 1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = REPORT_DIR / f"a_validation_{timestamp}.json"
    markdown_path = REPORT_DIR / f"a_validation_{timestamp}.md"
    report_paths = {
        "json": str(json_path),
        "markdown": str(markdown_path),
    }

    started = datetime.now(UTC)
    wall_started = time.perf_counter()
    if repeat == 1 and concurrency == 1:
        run = run_validation_once(run_index=1, timestamp=timestamp)
        report = build_single_report(run=run, report_paths=report_paths)
        exit_code = run.exit_code
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(run_validation_once, run_index=index, timestamp=timestamp)
                for index in range(1, repeat + 1)
            ]
            runs = [future.result() for future in concurrent.futures.as_completed(futures)]
        runs.sort(key=lambda item: item.run_index)
        report = build_stress_report(
            started_at=started.isoformat(),
            finished_at=datetime.now(UTC).isoformat(),
            wall_time_seconds=time.perf_counter() - wall_started,
            runs=runs,
            repeat=repeat,
            concurrency=concurrency,
            report_paths=report_paths,
        )
        exit_code = 0 if report["summary"]["failed_runs"] == 0 else 1

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown_report(report), encoding="utf-8")
    print_terminal_summary(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
