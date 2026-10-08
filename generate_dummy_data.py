
import csv
from pathlib import Path

OUTPUT = Path("test_data")
OUTPUT.mkdir(exist_ok=True)

STAGES = ["applied", "screened", "interviewed", "offered", "hired"]


def create_job(job_id, counts):
    """Create synthetic applications from cumulative counts."""
    if any(a < b for a, b in zip(counts, counts[1:])):
        raise ValueError("Counts must be non-increasing")

    rows = []

    for i, count in enumerate(counts):
        next_count = counts[i + 1] if i + 1 < 5 else 0

        for _ in range(count - next_count):
            rows.append({
                "job_id": job_id,
                "stage": STAGES[i],
                "days_in_process": (i + 1) * 5,
            })

    return rows


def save_csv(filename, rows):
    with (OUTPUT / filename).open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["job_id", "stage", "days_in_process"],
        )
        writer.writeheader()
        writer.writerows(rows)


# 1. Healthy funnel: all transitions >= 30%
normal = create_job("DATA_ANALYST", [100, 80, 60, 30, 12])
save_csv("normal.csv", normal)

# 2. Severe screening-to-interview bottleneck
bottleneck = create_job(
    "SOFTWARE_ENGINEER", [120, 95, 10, 3, 1]
)
save_csv("bottleneck.csv", bottleneck)

# 3. Too few candidates for reliable flagging
small = create_job("AI_INTERN", [8, 4, 1, 0, 0])
save_csv("small_sample.csv", small)

# 4. One invalid missing stage
missing = [row.copy() for row in normal]
missing[0]["stage"] = ""
save_csv("missing_values.csv", missing)

# 5. Unknown stage
invalid = [row.copy() for row in normal]
invalid[0]["stage"] = "teleported"
save_csv("invalid_stage.csv", invalid)

# 6. Empty dataset
save_csv("empty.csv", [])

print("Created 6 test datasets in test_data/")
