
from pathlib import Path

import pandas as pd
from anomaly_detector import detect_bottlenecks

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "test_data"


def load_data(filename):
    return pd.read_csv(DATA_DIR / filename)


def check_valid(filename, expected_statuses):
    df = load_data(filename)
    results = detect_bottlenecks(df)

    actual = {
        row["transition"]: row["status"]
        for row in results
    }

    assert actual == expected_statuses, (
        f"{filename}\n"
        f"Expected: {expected_statuses}\n"
        f"Actual:   {actual}"
    )

    print(f"PASS: {filename}")


def check_invalid(filename):
    df = load_data(filename)

    try:
        if df.empty:
            raise ValueError("Empty dataset")
        detect_bottlenecks(df)

    except ValueError:
        print(f"PASS: {filename} correctly rejected")
        return

    raise AssertionError(
        f"Invalid input was accepted: {filename}"
    )


check_valid(
    "normal.csv",
    {
        "applied → screened": "OK",
        "screened → interviewed": "OK",
        "interviewed → offered": "OK",
        "offered → hired": "OK",
    },
)

check_valid(
    "bottleneck.csv",
    {
        "applied → screened": "OK",
        "screened → interviewed": "REVIEW",
        "interviewed → offered": "OK",
        "offered → hired": "LOW_SAMPLE",
    },
)

check_valid(
    "small_sample.csv",
    {
        "applied → screened": "LOW_SAMPLE",
        "screened → interviewed": "LOW_SAMPLE",
        "interviewed → offered": "LOW_SAMPLE",
        "offered → hired": "LOW_SAMPLE",
    },
)

check_invalid("missing_values.csv")
check_invalid("invalid_stage.csv")
check_invalid("empty.csv")

print("\nAll 6 robustness scenarios passed.")
