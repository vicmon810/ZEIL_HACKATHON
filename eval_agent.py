
import os
import json
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from investigator import investigate

load_dotenv()

STAGES = [
    "applied", "screened", "interviewed",
    "offered", "hired"
]

# Cumulative hiring funnel counts
CASES = [
    ("normal", [100, 80, 60, 30, 12], False),
    ("screening_drop", [120, 95, 10, 3, 1], True),
    ("small_sample", [8, 4, 1, 0, 0], False),
    ("low_screening", [100, 15, 10, 5, 2], True),
    ("high_conversion", [60, 55, 45, 30, 20], False),
    ("zero_interviews", [80, 60, 0, 0, 0], True),
    ("low_offers", [100, 80, 60, 5, 2], True),
    ("low_hiring", [100, 70, 40, 20, 1], True),
    ("boundary_30", [100, 30, 12, 6, 3], False),
    ("boundary_29", [100, 29, 12, 6, 3], True),
]


def create_dataset(name, counts):
    rows = []

    for i, count in enumerate(counts):
        next_count = counts[i + 1] if i < 4 else 0

        for _ in range(count - next_count):
            rows.append({
                "job_id": name,
                "stage": STAGES[i],
                "days_in_process": (i + 1) * 5,
            })

    return pd.DataFrame(rows)


def evaluate():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    results = []

    for name, counts, expected_flag in CASES:
        print(f"\nTesting: {name}")

        df = create_dataset(name, counts)

        try:
            report, tool_log = investigate(df, api_key)

            bottleneck_calls = [
                entry for entry in tool_log
                if entry["tool"] == "find_bottlenecks"
            ]

            used_tool = len(tool_log) > 0
            used_detector = len(bottleneck_calls) > 0

            actual_flag = None

            if used_detector:
                findings = bottleneck_calls[-1]["result"]["findings"]
                actual_flag = any(
                    row["status"] == "REVIEW"
                    for row in findings
                )

            passed = (
                used_tool
                and used_detector
                and actual_flag == expected_flag
                and bool(report.strip())
            )

            result = {
                "case": name,
                "expected_flag": expected_flag,
                "actual_flag": actual_flag,
                "tool_used": used_tool,
                "detector_used": used_detector,
                "report_generated": bool(report.strip()),
                "passed": passed,
                "error": None,
            }

        except Exception as exc:
            result = {
                "case": name,
                "expected_flag": expected_flag,
                "passed": False,
                "error": str(exc),
            }

        results.append(result)
        print("PASS" if result["passed"] else "FAIL")

        # Avoid immediately hammering the shared quota.
        time.sleep(2)

    Path("eval_results").mkdir(exist_ok=True)

    output = Path("eval_results/agent_eval.json")
    output.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    passed = sum(r["passed"] for r in results)

    print(f"\nAgent evaluation: {passed}/{len(results)}")
    print(f"Results saved to {output}")


if __name__ == "__main__":
    evaluate()
