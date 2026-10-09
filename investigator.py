import pandas as pd 
from google import genai 
from google.genai import types
from tool_logger import save_tool_log
import logging
from anomaly_detector import detect_bottlenecks


BASELINE_PROMPT = """
You are Recruitment Data Detective.

Investigate recruitment funnel performance.
Use available analysis tools before presenting findings.

Compare jobs, identify potential bottlenecks,
and recommend three follow-up actions.

Use tool results for numerical claims.
Distinguish observations from hypotheses.
Do not claim causality or discrimination.
Explain uncertainty and sample-size limitations.
"""

IMPROVED_PROMPT = """
You are Recruitment Data Detective.

Follow this investigation protocol:

STEP 1: EVIDENCE COLLECTION
- Call find_bottlenecks before writing the report.
- Use compare_jobs to understand job-level differences.
- Call analyze_job when detailed evidence is needed.
- Never invent numerical evidence.

STEP 2: CLASSIFICATION
- REVIEW: conversion below 30%, previous count >= 10.
- LOW_SAMPLE: previous count below 10.
- OK: no flag under the configured rule.
- Never describe LOW_SAMPLE as proof of good performance.
- An OK status does not prove the hiring process is healthy.

STEP 3: REPORT
Present:
1. Observed evidence, with exact job IDs and rates.
2. Potential bottlenecks and their calculated status.
3. Hypotheses clearly marked as unverified.
4. Three practical follow-up actions.

STEP 4: SELF-CHECK
- Check every numerical statement against tool results.
- Do not claim causality or discrimination.
- Explain the rule's threshold and limitations.
- State when evidence is insufficient.
"""


def investigate(df: pd.DataFrame, api_key:str, prompt_version: str = "baseline"):
    """Run an evidence-base recuitment invesgigation"""
    stages = [
        "applied","screened","interviewed",
        "offered", "hired"
    ]

    ranks = {stage: i for i, stage in enumerate(stages) }

    data = df.copy()

    data["rank"] = data["stage"].map(ranks)

    tool_log = []

    def analyze_job(job_id:str) -> dict:
        """
        calculate the recuritment funnel for one job 
        agrs:
            job_id: the job ID to investigate
        """

        subset = data[data["job_id"].astype(str) == job_id]
        if subset.empty:
            return{"error": f"Unknow job: {job_id}"}

        counts = {
            stage: int((subset["rank"] >= i).sum())
            for i, stage in enumerate(stages)
        }

        total = len(subset)

        result = {
            "job_id": job_id,
            "applications": total,
            "stage_counts": counts,
            "interview_rate_pct": round(100*counts["interviewed"]/ total, 2),
            "hire_rate_pct": round(100*counts["hired"]/ total, 2),
            # "avg_days_in_process": round(float(subset["days_in_process"].mean(),2)),
            "avg_days_in_process": round(
              float(subset["days_in_process"].mean()), 2
            ),
        }

        tool_log.append({
            "tool":"analyze_job",
            "arguments":{"job_id": job_id},
            "result": result,
        })

        return result

    def compare_jobs() -> dict:
        """
        compare recruitment conversion rate across all jobs
        """
        results = []

        for job_id, group in data.groupby("job_id"):
            total = len(group)
            interviewed = int((group["rank"] >= 2).sum())
            hired = int((group["rank"] >= 4).sum())

            results.append({
                "job_id": str(job_id),
                "applications": total,
                "interview_rate_pct": round(
                    100 * interviewed / total, 2
                ),
                "hire_rate_pct": round(
                    100 * hired / total, 2
                ),
            })

        result = {"jobs": results}

        tool_log.append({
            "tool": "compare_jobs",
            "arguments": {},
            "result": result,
        })
        return result

    
    def find_bottlenecks() -> dict:
        """Detect potential recruitment funnel bottlenecks.

        Uses a documented conversion threshold and minimum
        sample size. Returns evidence for each job transition.
        """
        findings = detect_bottlenecks(data)

        result = {
            "method": (
                "Flag conversion below 30% when the "
                "previous stage has at least 10 candidates"
            ),
            "findings": findings,
        }

        tool_log.append({
            "tool": "find_bottlenecks",
            "arguments": {},
            "result": result,
        })

        return result
    

    job_ids = sorted(data["job_id"].astype(str).unique().tolist())
    if prompt_version not in {"baseline", "improved"}:
        raise ValueError("Unkown prompt version")

    selected_prompt = (
        BASELINE_PROMPT
        if prompt_version == "baseline"
        else IMPROVED_PROMPT
    )
    contents= selected_prompt + "\nAvaliable Job IDs:" + ", ".join(job_ids)
    client = genai.Client(api_key=api_key)

    try: 
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=contents,
            config=types.GenerateContentConfig(
            tools=[compare_jobs, analyze_job, find_bottlenecks],
            temperature=0.2# for stableibility
            ),
        )

        if not tool_log:
            raise RuntimeError(
                "Gemini Did not call any analysis tool."
            )

        if not response.text:
            raise RuntimeError(
                "Gemini returned no investigation report."
            )

        return response.text, tool_log

    finally:
        # client.close()
        try:
            save_tool_log(tool_log=tool_log)
        except(OSError, ValueError, TypeError) as exc:
            logging.warning("Failed to save tool logs: %s", exc)
        client.close()