
import pandas as pd
from anomaly_detector import detect_bottlenecks

BASE = "../test_data"

def check(filename, expected_status=None, should_fail=False):
    try:
        df = pd.read_csv(f"{BASE}/{filename}")

        if df.empty:
            raise ValueError("Empty dataset")

        results = detect_bottlenecks(df)
        statuses = {r["status"] for r in results}

        if should_fail:
            raise AssertionError("Invalid data was accepted")

        if expected_status is not None:
            assert expected_status in statuses, (
                f"Expected {expected_status}, got {statuses}"
            )

        print(f"PASS: {filename}")

    except (ValueError, pd.errors.ParserError):
        if should_fail:
            print(f"PASS: {filename} correctly rejected")
        else:
            raise


check("normal.csv", expected_status="OK")
check("bottleneck.csv", expected_status="REVIEW")
check("small_sample.csv", expected_status="LOW_SAMPLE")
check("missing_values.csv", should_fail=True)
check("invalid_stage.csv", should_fail=True)
check("empty.csv", should_fail=True)

print("All 6 robustness scenarios passed.")
