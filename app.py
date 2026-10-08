
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

st.set_page_config(
    page_title="Recruitment Data Detective",
    layout="wide",
)

STAGES = [
    "applied",
    "screened",
    "interviewed",
    "offered",
    "hired",
]

st.title("Recruitment Data Detective")
st.caption("AI-powered recruitment funnel investigation")

uploaded_file = st.file_uploader(
    "Upload recruitment data",
    type=["csv"],
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()

    required = {"job_id", "stage", "days_in_process"}

    if not required.issubset(df.columns):
        st.error(
            f"Required columns: {', '.join(sorted(required))}"
        )
        st.stop()

    if df.empty:
        st.error("The CSV file is empty.")
        st.stop()

    df["stage"] = df["stage"].astype(str).str.lower().str.strip()
    df["days_in_process"] = pd.to_numeric(
        df["days_in_process"], errors="coerce"
    )

    if not df["stage"].isin(STAGES).all():
        st.error("CSV contains unknown recruitment stages.")
        st.stop()

    if (
        df["job_id"].isna().any()
        or df["days_in_process"].isna().any()
        or (df["days_in_process"] < 0).any()
    ):
        st.error("Invalid job ID or processing days.")
        st.stop()

    st.subheader("Dataset overview")
    st.dataframe(df.head(20), use_container_width=True)

    stage_rank = {stage: i for i, stage in enumerate(STAGES)}
    df["stage_rank"] = df["stage"].map(stage_rank)

    counts = {
        stage: int((df["stage_rank"] >= i).sum())
        for i, stage in enumerate(STAGES)
    }

    total = len(df)
    interview_rate = counts["interviewed"] / total * 100
    offer_rate = counts["offered"] / total * 100
    hire_rate = counts["hired"] / total * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Applications", total)
    c2.metric("Interview rate", f"{interview_rate:.1f}%")
    c3.metric("Offer rate", f"{offer_rate:.1f}%")
    c4.metric("Hire rate", f"{hire_rate:.1f}%")

    st.subheader("Recruitment funnel")
    st.bar_chart(pd.Series(counts, name="Candidates"))

    st.subheader("Investigation")

    if st.button("Investigate with Gemini", type="primary"):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            st.error("GEMINI_API_KEY is not configured.")
            st.stop()

        summary = (
            f"Total applications: {total}\n"
            f"Stage counts (cumulative): {counts}\n"
            f"Interview rate: {interview_rate:.2f}%\n"
            f"Offer rate: {offer_rate:.2f}%\n"
            f"Hire rate: {hire_rate:.2f}%\n"
            f"Average days in process: "
            f"{df['days_in_process'].mean():.2f}\n"
        )

        prompt = f"""
You are an evidence-based recruitment data analyst.

Analyze these calculated recruitment metrics:

{summary}

Return:
1. Three notable findings.
2. Possible bottlenecks worth investigating.
3. Three practical recommendations for a hiring manager.

Important rules:
- Use only the provided calculated data.
- Do not invent statistics.
- Separate observed facts from possible explanations.
- Do not claim discrimination or causality without evidence.
- State when there is insufficient data.
- Recruitment stage counts are cumulative.
- Do not assume that low conversion is automatically bad.
"""

        with st.spinner("Gemini is investigating..."):
            client = None
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                if not response.text:
                    raise ValueError("Empty AI response")

                st.markdown(response.text)

            except Exception as exc:
                st.error(
                    f"Gemini request failed: "
                    f"{type(exc).__name__}: {exc}"
                )
            finally:
                if client is not None:
                    client.close()
