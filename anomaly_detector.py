
import pandas as pd

STAGES = [
    "applied",
    "screened",
    "interviewed",
    "offered",
    "hired",
]



def is_bottleneck(
    previous_count,
    next_count,
    threshold=0.30,
    minimum=10,
):
    """Return True when a valid transition falls below threshold."""

    if (
        previous_count < 0
        or next_count < 0
        or next_count > previous_count
    ):
        raise ValueError("Invalid funnel stage counts")

    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")

    if minimum < 1:
        raise ValueError("Minimum sample size must be positive")

    if previous_count < minimum:
        return False

    return next_count / previous_count < threshold


def detect_bottlenecks(df: pd.DataFrame) -> list[dict]:
    """Find potential bottlenecks for each job."""

    data = df.copy()

    required = {"job_id", "stage"}
    if not required.issubset(data.columns):
        raise ValueError("Missing job_id or stage")

    data["stage"] = (
        data["stage"].astype(str).str.lower().str.strip()
    )

    if not data["stage"].isin(STAGES).all():
        raise ValueError("Unknown recruitment stage")

    if data["job_id"].isna().any():
        raise ValueError("Missing job ID")

    stage_rank = {stage: i for i, stage in enumerate(STAGES)}
    data["rank"] = data["stage"].map(stage_rank)

    findings = []

    for job_id, group in data.groupby("job_id"):
        counts = {
            stage: int((group["rank"] >= i).sum())
            for i, stage in enumerate(STAGES)
        }

        for i in range(len(STAGES) - 1):
            previous_stage = STAGES[i]
            next_stage = STAGES[i + 1]

            previous = counts[previous_stage]
            following = counts[next_stage]

            rate = (
                following / previous * 100
                if previous > 0 else None
            )

            flagged = is_bottleneck(previous, following)

            findings.append({
                "job_id": str(job_id),
                "transition": (
                    f"{previous_stage} → {next_stage}"
                ),
                "previous_count": previous,
                "next_count": following,
                "conversion_pct": (
                    round(rate, 2) if rate is not None else None
                ),
                "status": "REVIEW" if flagged else (
                    "LOW_SAMPLE" if previous < 10 else "OK"
                ),
            })

    return findings
