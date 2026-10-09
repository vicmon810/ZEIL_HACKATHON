from gemini_voice_component import voice_navigation
import hashlib
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from anomaly_detector import detect_bottlenecks
from investigator import investigate

load_dotenv()
ROOT = Path(__file__).resolve().parent
STAGES = ['applied', 'screened', 'interviewed', 'offered', 'hired']
COLORS = ['#547963', '#69927A', '#8BAD86', '#BD9B75', '#A87958']

st.set_page_config(
    page_title='Recruitment Data Detective',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown('''
<style>
:root {color-scheme: light;}
.stApp {background: #F7F6F0; color: #303F32;}
[data-testid="stHeader"] {background: #F7F6F0;}
[data-testid="stSidebar"] {background: #EAF0E5; border-right: 1px solid #D6DFD1;}
[data-testid="stSidebar"] * {color: #314536;}
.block-container {max-width: 1370px; padding-top: 2rem; padding-bottom: 3rem;}
h1, h2, h3, h4, p, label {color: #304536;}
.hero {padding: 29px 33px; border-radius: 22px; background: linear-gradient(112deg,#E6EFE3 0%,#F3E9D9 100%); border: 1px solid #D6DDCB; margin-bottom: 24px;}
.eyebrow {font-size: .74rem; letter-spacing: .16em; font-weight: 750; color: #66816C; margin-bottom: 9px;}
.hero-title {font-size: clamp(1.7rem, 3vw, 2.5rem); color: #304B39; font-weight: 760; line-height: 1.2; margin: 0 0 10px;}
.hero-subtitle {color: #6D7565; font-size: 1rem; max-width: 700px; line-height: 1.6;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #E2E5DA; border-radius: 16px; padding: 18px 20px; box-shadow: 0 3px 12px rgba(49,67,48,.035);}
[data-testid="stMetricLabel"] {color: #6E796B;}
[data-testid="stMetricValue"] {color: #446C50;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap: 8px;}
[data-testid="stTabs"] button[role="tab"] {background: #EBEEE5; color: #566A59; border-radius: 12px 12px 0 0; padding: 11px 18px;}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {background: #D8E7D6; color: #2E5740; font-weight: 700;}
.stButton button[kind="primary"] {background: #557B60; color: white; border: 1px solid #557B60; border-radius: 12px; padding: .7rem 1.3rem; font-weight: 700;}
.stButton button[kind="primary"]:hover {background: #436A51; border-color: #436A51; color: white;}
[data-testid="stExpander"], [data-testid="stDataFrame"] {border-radius: 12px;}
.section-kicker {color: #8E7860; font-size: .78rem; text-transform: uppercase; font-weight: 750; letter-spacing: .13em; padding: 8px 0 10px;}
.finding-card {background: #FFF8EE; border: 1px solid #E6D7C1; border-left: 5px solid #B88B5C; border-radius: 13px; padding: 16px 18px; margin: 12px 0; color: #5D4B3B;}
.muted-note {background:#EDF3E9; border: 1px solid #D8E5D5; border-radius: 12px; padding: 14px 17px; color: #516B55; font-size: .92rem;}
</style>
''', unsafe_allow_html=True)

if 'report' not in st.session_state:
    st.session_state.report = None
if 'tool_log' not in st.session_state:
    st.session_state.tool_log = []
if 'data_signature' not in st.session_state:
    st.session_state.data_signature = None


def validate_data(frame: pd.DataFrame) -> pd.DataFrame:
    required = {'job_id', 'stage', 'days_in_process'}
    if frame.empty:
        raise ValueError('The dataset is empty.')
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f'Missing required columns: {", ".join(sorted(missing))}')
    data = frame.copy()
    data['stage'] = data['stage'].astype(str).str.strip().str.lower()
    data['days_in_process'] = pd.to_numeric(data['days_in_process'], errors='coerce')
    if not data['stage'].isin(STAGES).all():
        raise ValueError('Invalid or missing recruitment stage.')
    if data['job_id'].isna().any() or data['job_id'].astype(str).str.strip().eq('').any():
        raise ValueError('Missing job ID.')
    if data['days_in_process'].isna().any() or (data['days_in_process'] < 0).any():
        raise ValueError('Invalid or negative days_in_process.')
    return data


# Apply a voice-requested dataset before the sidebar widgets are instantiated.
# Widget state cannot safely be changed after the widget is created.
VOICE_DATASETS = {
    "bottleneck": "Screening Bottleneck",
    "normal": "Healthy Funnel",
    "small_sample": "Small Sample",
}
pending = st.session_state.pop("pending_voice_dataset", None)
if pending in VOICE_DATASETS:
    st.session_state["data_source_choice"] = "Demo Dataset"
    st.session_state["demo_dataset_choice"] = VOICE_DATASETS[pending]

with st.sidebar:
    st.markdown('## 🌿 Data Detective')
    st.caption('Recruitment Intelligence')
    st.divider()
    source = st.radio('Data source', ['Demo Dataset', 'Upload CSV'], key="data_source_choice")
    if source == 'Demo Dataset':
        options = {
            'Screening Bottleneck': 'bottleneck.csv',
            'Healthy Funnel': 'normal.csv',
            'Small Sample': 'small_sample.csv',
        }
        selection = st.selectbox('Scenario', list(options), key="demo_dataset_choice")
        file_path = ROOT / 'test_data' / options[selection]
        if not file_path.is_file():
            st.error(f'Missing test dataset: {file_path.name}')
            st.stop()
        file_bytes = file_path.read_bytes()
    else:
        uploaded = st.file_uploader('Upload recruitment CSV', type=['csv'])
        if uploaded is None:
            st.info('Choose a CSV file to begin.')
            st.stop()
        if uploaded.size > 2 * 1024 * 1024:
            st.error('Maximum upload size is 2 MB.')
            st.stop()
        file_bytes = uploaded.getvalue()

    import io
    try:
        df = validate_data(pd.read_csv(io.BytesIO(file_bytes)))
    except (ValueError, pd.errors.ParserError, UnicodeError, pd.errors.EmptyDataError) as exc:
        st.error(f'Invalid CSV: {exc}')
        st.stop()

    signature = hashlib.sha256(file_bytes).hexdigest()
    if st.session_state.data_signature != signature:
        st.session_state.data_signature = signature
        st.session_state.report = None
        st.session_state.tool_log = []

    st.divider()
    st.markdown('**Detection settings**')
    st.caption('Review threshold: < 30%')
    st.caption('Minimum previous-stage count: 10')
    st.caption('AI: Gemini Flash')
    st.divider()
    st.caption('ZEIL Hackathon 2026')
    st.caption('Use synthetic data for demos.')

st.markdown('''
<div class="hero">
  <div class="eyebrow">PEOPLE ANALYTICS · AI INVESTIGATION</div>
  <div class="hero-title">Recruitment Data Detective</div>
  <div class="hero-subtitle">A calmer, clearer way to investigate hiring funnels. Discover unusual transitions, inspect supporting evidence, and ask Gemini to explain what deserves attention.</div>
</div>
''', unsafe_allow_html=True)

ranks = {name: i for i, name in enumerate(STAGES)}
ranked = df['stage'].map(ranks)
counts = {name: int((ranked >= i).sum()) for i, name in enumerate(STAGES)}
total = len(df)
findings = detect_bottlenecks(df)
findings_df = pd.DataFrame(findings)
flagged_df = findings_df[findings_df['status'] == 'REVIEW']
low_sample_count = int((findings_df['status'] == 'LOW_SAMPLE').sum())

# Gemini Live returns structured navigation events through Components V2.
if "active_page" not in st.session_state:
    st.session_state.active_page = "Overview"
voice_event = voice_navigation()
command = getattr(voice_event, "command", None)
if command and command != st.session_state.get("last_voice_command"):
    st.session_state.last_voice_command = command
    target = command.split(":", 1)[0]
    if target.startswith("dataset|"):
        dataset_id = target.split("|", 1)[1]
        if dataset_id in VOICE_DATASETS:
            st.session_state.pending_voice_dataset = dataset_id
            st.rerun()
    if target == "investigate_now":
        st.session_state.active_page = "AI Investigation"
        st.session_state.pending_voice_investigation = True
    destinations = {
        "overview": "Overview",
        "anomalies": "Anomaly Detection",
        "investigation": "AI Investigation",
    }
    if target in destinations:
        st.session_state.active_page = destinations[target]

st.segmented_control(
    "Dashboard section",
    ["Overview", "Anomaly Detection", "AI Investigation"],
    key="active_page", label_visibility="collapsed",
)

if st.session_state.active_page == "Overview":
    st.markdown('<div class="section-kicker">Hiring funnel overview</div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric('Applications', f'{total:,}')
    b.metric('Interview rate', f'{counts["interviewed"] / total:.1%}')
    c.metric('Offer rate', f'{counts["offered"] / total:.1%}')
    d.metric('Hire rate', f'{counts["hired"] / total:.1%}')
    st.markdown('### Candidate journey')
    fig = go.Figure(go.Funnel(
        y=[x.title() for x in STAGES],
        x=[counts[x] for x in STAGES],
        textinfo='value+percent initial',
        marker={'color': COLORS, 'line': {'color': '#F7F6F0', 'width': 2}},
        textfont={'color': '#FFFFFF', 'size': 14},
    ))
    fig.update_layout(
        paper_bgcolor='#F7F6F0', plot_bgcolor='#F7F6F0',
        font={'color': '#455A49'}, height=410,
        margin={'l': 15, 'r': 15, 't': 20, 'b': 15},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('### Data preview')
    st.dataframe(df[['job_id', 'stage', 'days_in_process']].head(20),
                 use_container_width=True, hide_index=True)

if st.session_state.active_page == "Anomaly Detection":
    st.markdown('<div class="section-kicker">Evidence-based monitoring</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.metric('Jobs analyzed', df['job_id'].nunique())
    b.metric('Review flags', len(flagged_df))
    c.metric('Low-sample transitions', low_sample_count)
    st.markdown('### Potential bottlenecks')
    if flagged_df.empty:
        st.success('No conversion transitions were flagged under the current rule.')
    else:
        st.warning(f'{len(flagged_df)} transition(s) need review.')
        for _, item in flagged_df.iterrows():
            # Render candidate-supplied job IDs as ordinary text, not HTML.
            with st.container(border=True):
                st.markdown(f'**Job:** `{item["job_id"]}`')
                st.write(item['transition'])
                st.metric('Conversion rate', f'{item["conversion_pct"]:.2f}%')
                st.caption('REVIEW · Consider investigating this stage transition')
    st.dataframe(findings_df, use_container_width=True, hide_index=True)
    st.markdown('''<div class="muted-note">A REVIEW flag means conversion is below 30% with at least 10 people in the preceding stage. LOW_SAMPLE indicates insufficient volume for this rule. These are investigation signals, not evidence of causality or discrimination.</div>''', unsafe_allow_html=True)

if st.session_state.active_page == "AI Investigation":
    st.markdown('<div class="section-kicker">Evidence-first AI assistant</div>', unsafe_allow_html=True)
    st.markdown('### Gemini Investigation Agent')
    st.write('Run an investigation using Python-based analysis tools. Results remain visible while you switch between tabs.')
    voice_start = st.session_state.pop("pending_voice_investigation", False)
    manual_start = st.button(
        'Start AI Investigation', type='primary', use_container_width=True
    )
    if voice_start or manual_start:
        key = os.getenv('GEMINI_API_KEY')
        if not key:
            st.error('GEMINI_API_KEY is missing. Add it to your local .env file.')
        else:
            with st.spinner('Investigating recruitment funnel...'):
                try:
                    report, tool_log = investigate(df, key)
                    st.session_state.report = report
                    st.session_state.tool_log = tool_log
                except Exception as exc:
                    st.error(f'Gemini investigation failed: {type(exc).__name__}: {exc}')

    if st.session_state.report:
        st.markdown('### Investigation Report')
        with st.container(border=True):
            st.markdown(st.session_state.report)
        with st.expander('Agent Execution Trace · Function Calling', expanded=False):
            for i, entry in enumerate(st.session_state.tool_log, 1):
                st.markdown(f'**Step {i}: {entry["tool"]}**')
                st.caption('Arguments')
                st.json(entry['arguments'])
                st.caption('Calculated evidence')
                st.json(entry['result'])
    else:
        st.info('Choose a scenario and click Start AI Investigation to generate an evidence-based report.')
