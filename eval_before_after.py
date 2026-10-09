
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from eval_agent import CASES, create_dataset
from investigator import investigate

load_dotenv()

OUT = Path("eval_results")
OUT.mkdir(exist_ok=True)


def run_case(name, counts, expected, version, api_key):
    df = create_dataset(name, counts)

    result = {
        "case": name,
        "version": version,
        "expected_flag": expected,
        "status": "FAIL",
        "tool_used": False,
        "detector_used": False,
        "actual_flag": None,
        "report_generated": False,
        "error": None,
    }

    try:
        report, logs = investigate(
            df,
            api_key,
            prompt_version=version,
        )

        detector_calls = [
            x for x in logs
            if x["tool"] == "find_bottlenecks"
        ]

        result["tool_used"] = bool(logs)
        result["detector_used"] = bool(detector_calls)
        result["report_generated"] = bool(report.strip())

        if detector_calls:
            findings = detector_calls[-1]["result"]["findings"]
            result["actual_flag"] = any(
                f["status"] == "REVIEW" for f in findings
            )

        correct = (
            result["tool_used"]
            and result["detector_used"]
            and result["report_generated"]
            and result["actual_flag"] == expected
        )

        result["status"] = "PASS" if correct else "FAIL"
        result["report"] = report

    except Exception as exc:
        message = str(exc)
        result["error"] = message

        if (
            "503 UNAVAILABLE" in message
            or "429 RESOURCE_EXHAUSTED" in message
        ):
            result["status"] = "API_ERROR"

    return result


def summarize(records, version):
    subset = [r for r in records if r["version"] == version]

    passed = sum(r["status"] == "PASS" for r in subset)
    failed = sum(r["status"] == "FAIL" for r in subset)
    api_errors = sum(
        r["status"] == "API_ERROR" for r in subset
    )

    completed = passed + failed

    return {
        "version": version,
        "total": len(subset),
        "passed": passed,
        "failed": failed,
        "api_errors": api_errors,
        "completion_rate": (
            round(completed / len(subset), 3) if subset else None
        ),
        "pass_rate_completed": (
            round(passed / completed, 3)
            if completed else None
        ),
    }


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    records = []

    # Interleave both versions to reduce time-related bias.
    for name, counts, expected in CASES:
        for version in ("baseline", "improved"):
            print(f"Testing {name}: {version}", flush=True)

            result = run_case(
                name, counts, expected, version, api_key
            )

            records.append(result)
            print(f"  Result: {result['status']}", flush=True)

            # Save after every case so partial results survive.
            (OUT / "paired_raw.json").write_text(
                json.dumps(records, indent=2),
                encoding="utf-8",
            )

            if result["status"] == "API_ERROR":
                print(
                    "API unavailable or rate-limited. "
                    "Stopping to protect shared quota."
                )
                return

            time.sleep(3)

    summaries = {
        version: summarize(records, version)
        for version in ("baseline", "improved")
    }

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gemini-flash-latest",
        "temperature": 0.2,
        "metrics": summaries,
        "results": records,
    }

    (OUT / "before_after.json").write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print("\n=== BEFORE / AFTER ===")
    for version, stats in summaries.items():
        print(version, stats)


if __name__ == "__main__":
    main()
