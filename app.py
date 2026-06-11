"""
Streamlit demo UI for the Candidate Ranking System.

Recruiter-friendly interface showing the JD, ranked candidates,
score breakdowns, and filtering options. Styled with the Bitcoin DeFi
design system: dark void background, orange accents, glass morphism.

Usage:
    streamlit run app.py
"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path


# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Redrob AI Candidate Ranker",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Custom CSS ───────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Calistoga&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Global ─────────────────────────────────────── */
    .stApp {
        background-color: #FAFAFA;
        font-family: 'Inter', sans-serif;
        color: #0F172A;
    }

    /* ── Typography ────────────────────────────────── */
    h1, h2, h3 {
        font-family: 'Calistoga', cursive !important;
        color: #0F172A !important;
        font-weight: normal !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-size: 2.8rem !important;
        background: linear-gradient(135deg, #0052FF, #4D7CFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        display: inline-block;
    }

    /* ── Metrics ───────────────────────────────────── */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
        border-color: #0052FF;
    }

    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: #0052FF !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        color: #64748B !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.75rem !important;
        font-weight: 600;
    }

    /* ── Sidebar ───────────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0;
    }

    /* ── Buttons ───────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #0052FF, #4D7CFF) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.5rem !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(0, 82, 255, 0.2) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 82, 255, 0.3) !important;
    }

    /* ── Score bar utility ────────────────────────── */
    .score-bar-bg {
        height: 4px;
        border-radius: 2px;
        background: #F1F5F9;
        width: 100%;
        overflow: hidden;
    }

    .candidate-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        animation: fadeUp 0.4s ease-out forwards;
    }

    .candidate-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.08);
        border-color: #CBD5E1;
    }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .rank-badge {
        display: inline-block;
        background: #F1F5F9;
        color: #475569;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
    }

    .rank-badge-gold {
        display: inline-block;
        background: linear-gradient(135deg, #0052FF, #4D7CFF);
        color: white;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 6px;
        box-shadow: 0 4px 10px rgba(0, 82, 255, 0.2);
    }

    .score-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .score-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .muted {
        color: #64748B;
    }

    /* Smooth dataframe borders */
    [data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
    }
    
    hr {
        border-color: #E2E8F0 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Data loading ─────────────────────────────────────────────────────────
@st.cache_data
def load_results():
    """Load the ranked results if they exist."""
    detailed = Path("outputs/detailed_results.csv")
    submission = Path("outputs/submission.csv")

    if detailed.exists():
        return pd.read_csv(detailed, encoding="utf-8")
    elif submission.exists():
        return pd.read_csv(submission, encoding="utf-8")
    return None


@st.cache_data
def load_jd():
    """Load the structured JD."""
    jd_path = Path("data/jd.json")
    if jd_path.exists():
        with open(jd_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data
def load_candidates_sample():
    """Load sample candidates for display context."""
    sample_path = Path(
        "[PUB] India_runs_data_and_ai_challenge/"
        "India_runs_data_and_ai_challenge/sample_candidates.json"
    )
    if sample_path.exists():
        with open(sample_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ── Helper: render score bar ─────────────────────────────────────────────
def score_bar_html(label: str, value: float, max_val: float = 1.0) -> str:
    pct = min(100, (value / max_val) * 100)
    color = "#10B981" if pct >= 80 else "#0052FF" if pct >= 50 else "#94A3B8"
    return f"""<div style="margin-bottom: 8px;">
<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
<span class="score-label">{label}</span>
<span class="score-value" style="color: {color};">{value:.3f}</span>
</div>
<div class="score-bar-bg">
<div style="width:{pct:.0f}%; height:4px; border-radius:2px; background:linear-gradient(90deg, {color} 0%, {color}CC 100%);"></div>
</div>
</div>"""


# ── Main app ─────────────────────────────────────────────────────────────
def main():
    inject_custom_css()

    # Header
    st.markdown("""
    <div style="text-align: center; padding: 40px 0 20px 0;">
        <h1 style="margin-bottom: 8px;">
            Candidate Discovery Engine
        </h1>
        <p class="muted" style="font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            Intelligent ranking for the <strong>Senior AI Engineer</strong> role. 
            Powered by semantic retrieval and multi-dimensional analysis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Load data
    results = load_results()
    jd = load_jd()

    if results is None:
        st.warning(
            "⚠️ No ranking results found. Run the ranking pipeline first:\n\n"
            "```bash\n"
            "python precompute.py --candidates path/to/candidates.jsonl\n"
            "python rank.py --candidates path/to/candidates.jsonl --out outputs/submission.csv\n"
            "```"
        )
        return

    # ── Sidebar: Filters ─────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Filters")

        min_score = st.slider(
            "Minimum Score", 0.0, 1.0, 0.0, 0.01,
            help="Only show candidates above this score threshold"
        )

        max_results = st.slider(
            "Show Top N", 10, 100, 25, 5,
            help="Number of candidates to display"
        )

        # Score dimension filter
        sort_by = st.selectbox(
            "Sort By",
            ["Final Score", "Semantic", "Skills", "Experience",
             "Career", "Behavioral", "Location"],
            help="Re-sort candidates by a specific scoring dimension"
        )

        st.divider()
        st.markdown("### Score Distribution")

        if "score" in results.columns:
            import plotly.express as px
            fig = px.histogram(
                results, x="score", nbins=20,
                color_discrete_sequence=["#0052FF"],
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#64748B",
                xaxis_title="Score",
                yaxis_title="Count",
                margin=dict(l=10, r=10, t=10, b=10),
                height=200,
            )
            fig.update_xaxes(gridcolor="#F1F5F9")
            fig.update_yaxes(gridcolor="#F1F5F9")
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Download button
        csv_data = results[["candidate_id", "rank", "score", "reasoning"]].to_csv(
            index=False
        )
        st.download_button(
            "Download Submission CSV",
            csv_data,
            "submission.csv",
            "text/csv",
        )

    # ── Main content: two columns ────────────────────────────────────
    col_jd, col_results = st.columns([1, 2])

    # ── Left column: JD ──────────────────────────────────────────────
    with col_jd:
        st.markdown("### Job Description")
        if jd:
            st.markdown(f"""<div class="candidate-card" style="margin-top: 8px;">
<div style="font-family:'Calistoga',cursive; font-size:1.4rem; color:#0F172A; margin-bottom:4px;">{jd.get('title', '')}</div>
<div class="muted" style="font-size:0.9rem; margin-bottom:16px;">{jd.get('company', '')} · {jd.get('company_stage', '')} · {jd.get('location_text', '')}</div>
<div style="font-size:0.9rem; color:#475569; margin-bottom:10px;">
<strong style="color:#0F172A;">Experience:</strong> {jd.get('experience_range', {}).get('min', '?')}–{jd.get('experience_range', {}).get('max', '?')} years
</div>
</div>""", unsafe_allow_html=True)

            with st.expander("Must-Have Skills", expanded=True):
                for skill in jd.get("must_have_skills", []):
                    st.markdown(f"- {skill}")

            with st.expander("Nice-To-Have Skills"):
                for skill in jd.get("nice_to_have_skills", []):
                    st.markdown(f"- {skill}")

            with st.expander("Disqualifiers"):
                for d in jd.get("disqualifiers", []):
                    st.markdown(f"- {d}")

            with st.expander("Ideal Candidate Profile"):
                st.markdown(jd.get("ideal_candidate_profile", ""))

    # ── Right column: Ranked candidates ──────────────────────────────
    with col_results:
        # Apply filters
        filtered = results[results["score"] >= min_score].head(max_results)

        # Sort
        sort_map = {
            "Final Score": "score",
            "Semantic": "semantic_score",
            "Skills": "skill_score",
            "Experience": "experience_score",
            "Career": "career_score",
            "Behavioral": "behavioral_score",
            "Location": "location_score",
        }
        sort_col = sort_map.get(sort_by, "score")
        if sort_col in filtered.columns:
            filtered = filtered.sort_values(sort_col, ascending=False)

        st.markdown(f"### Top Candidates ({len(filtered)} shown)")

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Ranked", len(results))
        with m2:
            st.metric("Avg Score", f"{results['score'].mean():.3f}")
        with m3:
            st.metric("Top Score", f"{results['score'].max():.3f}")
        with m4:
            above_70 = len(results[results["score"] >= 0.7])
            st.metric("Score ≥ 0.7", above_70)

        st.markdown("")

        # Render candidate cards
        for _, row in filtered.iterrows():
            rank = int(row["rank"])
            badge_class = "rank-badge-gold" if rank <= 3 else "rank-badge"

            # Build score breakdown
            score_bars = ""
            score_cols = [
                ("Semantic", "semantic_score"),
                ("Skills", "skill_score"),
                ("Experience", "experience_score"),
                ("Career", "career_score"),
                ("Behavioral", "behavioral_score"),
                ("Location", "location_score"),
                ("Education", "education_score"),
            ]
            for label, col in score_cols:
                if col in row.index and pd.notna(row[col]):
                    score_bars += score_bar_html(label, row[col])

            reasoning = row.get("reasoning", "")

            st.markdown(f"""<div class="candidate-card">
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
<div style="display:flex; align-items:center; gap:12px;">
<span class="{badge_class}">#{rank}</span>
<span class="mono" style="font-size:1.05rem; color:#0F172A; font-weight: 600;">{row['candidate_id']}</span>
</div>
<div style="text-align: right;">
<span class="mono" style="font-size:1.4rem; color:#0052FF; font-weight:700;">{row['score']:.4f}</span>
<div class="score-label" style="font-size: 0.65rem; margin-top: 2px;">Final Score</div>
</div>
</div>

<div style="font-size:0.95rem; color:#334155; margin-bottom:24px; line-height:1.6; border-left:3px solid #0052FF; padding-left:16px; background: linear-gradient(90deg, #F8FAFC 0%, transparent 100%); padding-top: 8px; padding-bottom: 8px; border-radius: 0 8px 8px 0;">
{reasoning}
</div>

<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px 32px;">
{score_bars}
</div>
</div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
