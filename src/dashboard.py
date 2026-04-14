"""
FDA Drug Shortage Supply Chain Risk Dashboard
===============================================
Interactive Streamlit dashboard for non-technical government stakeholders.
Four views: Risk Leaderboard, Shortage Reason Breakdown, Therapeutic Category
Analysis, and Time-Series View.

Mirrors Exiger's delivery model — custom reports and dashboards for
policymakers, agencies, and operational users.

Author: Alexander Peralta
Usage: streamlit run src/dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from collections import Counter, defaultdict


# ─── CONFIG ──────────────────────────────────────────────

st.set_page_config(
    page_title="FDA Drug Shortage Risk Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .block-container { padding-top: 2.5rem; }
    header[data-testid="stHeader"] { background-color: #0e1117; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }
    .stMetric { background-color: #0e1117; border-radius: 8px; padding: 12px; border: 1px solid #1e2d4a; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
</style>
""", unsafe_allow_html=True)

RISK_COLORS = {"CRITICAL": "#ef4444", "HIGH": "#f59e0b", "MODERATE": "#3b82f6", "LOW": "#10b981"}
REASON_COLORS = {
    "Raw Material / API Shortage": "#ef4444",
    "Manufacturing / Quality": "#f97316",
    "Discontinuation": "#8b5cf6",
    "Demand Increase": "#f59e0b",
    "Shipping / Logistics Delay": "#06b6d4",
    "Regulatory": "#ec4899",
    "Other / Unspecified": "#6b7280",
}


# ─── DATA LOADING ────────────────────────────────────────

@st.cache_data
def load_data():
    """Load processed data files."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    scores_path = os.path.join(base, "data", "processed", "drug_risk_scores.json")
    clean_path = os.path.join(base, "data", "processed", "fda_shortages_cleaned.json")
    anomaly_path = os.path.join(base, "data", "processed", "anomaly_results.json")

    # Check if processed data exists, if not run pipeline
    if not os.path.exists(scores_path):
        st.error("Processed data not found. Run `python main.py` first to generate the data.")
        st.stop()

    with open(scores_path) as f:
        drug_scores = json.load(f)
    with open(clean_path) as f:
        cleaned = json.load(f)

    anomaly_data = None
    if os.path.exists(anomaly_path):
        with open(anomaly_path) as f:
            anomaly_data = json.load(f)

    return drug_scores, cleaned, anomaly_data


drug_scores, cleaned_records, anomaly_data = load_data()
df_scores = pd.DataFrame(drug_scores)
df_records = pd.DataFrame(cleaned_records)


# ─── SIDEBAR ─────────────────────────────────────────────

st.sidebar.markdown("## ⚡ Risk Dashboard")
st.sidebar.markdown("**FDA Drug Shortage**  \nSupply Chain Risk Analysis")
st.sidebar.markdown("---")

view = st.sidebar.radio(
    "Dashboard View",
    ["📊 Risk Leaderboard", "◉ Shortage Causes", "△ Category Analysis",
     "◇ Time Series", "□ Supplier Risk", "◈ Methodology"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Data Source**")
st.sidebar.markdown("FDA openFDA API  \n`api.fda.gov/drug/shortages`")
st.sidebar.markdown(f"**{len(cleaned_records):,}** shortage records  \n**{len(drug_scores)}** drugs scored")
st.sidebar.markdown("---")
st.sidebar.markdown("*Alexander Peralta*  \nahperalt@gmail.com")


# ─── HEADER METRICS ──────────────────────────────────────

st.markdown("## ⚡ FDA Drug Shortage — Supply Chain Risk Dashboard")
st.markdown("")

col1, col2, col3, col4, col5, col6 = st.columns(6)
active = sum(1 for r in cleaned_records if r["status"] == "Current")
critical = sum(1 for d in drug_scores if d["risk_level"] == "CRITICAL")
high = sum(1 for d in drug_scores if d["risk_level"] == "HIGH")
durations = [r["duration_days"] for r in cleaned_records if r["duration_days"] > 0]
avg_dur = int(np.mean(durations)) if durations else 0

col1.metric("Total Records", f"{len(cleaned_records):,}")
col2.metric("Unique Drugs", len(drug_scores))
col3.metric("Active Shortages", f"{active:,}")
col4.metric("Critical Risk", critical)
col5.metric("High Risk", high)
col6.metric("Avg Duration", f"{avg_dur // 365}y {(avg_dur % 365) // 30}m")

st.markdown("---")


# ─── VIEW: RISK LEADERBOARD ─────────────────────────────

if view == "📊 Risk Leaderboard":
    st.markdown("### Risk Leaderboard")
    st.markdown("Composite risk = 30% Recurrence + 25% Duration + 25% Cause Severity + 20% Status")

    # Filters
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        status_filter = st.selectbox("Status", ["All", "Active Shortage", "Resolved/Discontinued"])
    with fcol2:
        categories = sorted(df_scores["primary_category"].unique())
        cat_filter = st.selectbox("Category", ["All"] + categories)
    with fcol3:
        risk_filter = st.selectbox("Risk Level", ["All", "CRITICAL", "HIGH", "MODERATE", "LOW"])
    with fcol4:
        sort_by = st.selectbox("Sort By", ["risk_score", "recurrence_count", "avg_duration_days", "num_companies"])

    # Apply filters
    df_filtered = df_scores.copy()
    if status_filter != "All":
        df_filtered = df_filtered[df_filtered["current_status"] == status_filter]
    if cat_filter != "All":
        df_filtered = df_filtered[df_filtered["primary_category"] == cat_filter]
    if risk_filter != "All":
        df_filtered = df_filtered[df_filtered["risk_level"] == risk_filter]

    df_filtered = df_filtered.sort_values(sort_by, ascending=False).reset_index(drop=True)

    st.markdown(f"**{len(df_filtered)} drugs** matching filters")

    # Display table
    display_cols = ["drug", "risk_score", "risk_level", "recurrence_count",
                    "avg_duration_days", "primary_reason", "current_status",
                    "primary_category", "num_companies"]

    st.dataframe(
        df_filtered[display_cols].rename(columns={
            "drug": "Drug",
            "risk_score": "Risk Score",
            "risk_level": "Level",
            "recurrence_count": "Recurrence",
            "avg_duration_days": "Avg Duration (d)",
            "primary_reason": "Primary Cause",
            "current_status": "Status",
            "primary_category": "Category",
            "num_companies": "Suppliers",
        }),
        use_container_width=True,
        height=600,
    )

    # Risk score distribution
    st.markdown("### Risk Score Distribution")
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.set_facecolor("#0e1117")
    fig.patch.set_facecolor("#0e1117")

    bins = np.arange(0, 105, 5)
    colors = []
    for b in bins[:-1]:
        if b >= 70: colors.append("#ef4444")
        elif b >= 50: colors.append("#f59e0b")
        elif b >= 30: colors.append("#3b82f6")
        else: colors.append("#10b981")

    n, _, patches = ax.hist(df_scores["risk_score"], bins=bins, edgecolor="#1e2d4a", linewidth=0.5)
    for patch, color in zip(patches, colors):
        patch.set_facecolor(color)

    ax.set_xlabel("Composite Risk Score", color="#8899b4", fontsize=9)
    ax.set_ylabel("Drug Count", color="#8899b4", fontsize=9)
    ax.tick_params(colors="#8899b4", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#1e2d4a")
    ax.spines["bottom"].set_color("#1e2d4a")
    st.pyplot(fig)

    # Drug detail expander
    st.markdown("### Drug Detail")
    selected_drug = st.selectbox(
        "Select a drug for detailed breakdown",
        df_filtered["drug"].tolist() if len(df_filtered) > 0 else [],
    )
    if selected_drug:
        drug = next(d for d in drug_scores if d["drug"] == selected_drug)

        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        dcol1.metric("Recurrence Score", f"{drug['recurrence_score']}/100", f"{drug['recurrence_count']}× events")
        dcol2.metric("Duration Score", f"{drug['duration_score']}/100", f"{drug['avg_duration_days']} avg days")
        dcol3.metric("Cause Severity", f"{drug['cause_severity_score']}/100", drug['primary_reason'])
        dcol4.metric("Status Score", f"{drug['status_score']}/100", drug['current_status'])

        st.markdown(f"**Suppliers:** {', '.join(drug['companies'])}")
        st.markdown(f"**Therapeutic areas:** {', '.join(drug['all_categories'])}")
        st.markdown(f"**All causes observed:** {', '.join(drug['all_reasons'])}")


# ─── VIEW: SHORTAGE CAUSES ──────────────────────────────

elif view == "◉ Shortage Causes":
    st.markdown("### Shortage Reason Breakdown")
    st.markdown("Standardized shortage causes across all records")

    reason_counts = df_records["shortage_reason"].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_facecolor("#0e1117")
        fig.patch.set_facecolor("#0e1117")

        colors = [REASON_COLORS.get(r, "#6b7280") for r in reason_counts.index]
        wedges, texts, autotexts = ax.pie(
            reason_counts.values, labels=None, autopct="%1.1f%%",
            colors=colors, startangle=90, pctdistance=0.75,
            wedgeprops=dict(width=0.5, edgecolor="#0e1117", linewidth=2),
        )
        for t in autotexts:
            t.set_color("white")
            t.set_fontsize(8)
        ax.set_title("Distribution of Shortage Causes", color="white", fontsize=11, pad=15)
        st.pyplot(fig)

    with col2:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_facecolor("#0e1117")
        fig.patch.set_facecolor("#0e1117")

        y_pos = range(len(reason_counts))
        bars = ax.barh(y_pos, reason_counts.values, color=colors, edgecolor="#1e2d4a", height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(reason_counts.index, color="#8899b4", fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Number of Records", color="#8899b4", fontsize=9)
        ax.tick_params(colors="#8899b4", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#1e2d4a")
        ax.spines["bottom"].set_color("#1e2d4a")

        for bar, val in zip(bars, reason_counts.values):
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", color="#8899b4", fontsize=9)

        ax.set_title("Shortage Records by Cause", color="white", fontsize=11, pad=15)
        st.pyplot(fig)

    # Cause severity table
    st.markdown("### Cause Severity Mapping")
    severity_df = pd.DataFrame([
        {"Cause": k, "Severity Score": int(v * 100), "Rationale": r}
        for k, v, r in [
            ("Raw Material / API Shortage", 1.0, "Upstream dependency failure — hardest to resolve"),
            ("Manufacturing / Quality", 0.85, "GMP violations, facility shutdowns"),
            ("Discontinuation", 0.80, "Permanent supply loss"),
            ("Regulatory", 0.70, "Compliance-driven disruption"),
            ("Shipping / Logistics Delay", 0.50, "Usually transient"),
            ("Demand Increase", 0.40, "Demand-side spike, typically temporary"),
            ("Other / Unspecified", 0.50, "Insufficient signal for classification"),
        ]
    ])
    st.dataframe(severity_df, use_container_width=True, hide_index=True)


# ─── VIEW: CATEGORY ANALYSIS ────────────────────────────

elif view == "△ Category Analysis":
    st.markdown("### Therapeutic Category Analysis")
    st.markdown("Z-score anomaly detection — categories with |z| > 1.5 flagged as statistically anomalous")

    if anomaly_data and "category_anomalies" in anomaly_data:
        cat_data = anomaly_data["category_anomalies"]
    else:
        # Compute on the fly
        cat_counts = Counter()
        for r in cleaned_records:
            for c in r["therapeutic_categories"]:
                cat_counts[c] += 1
        counts = np.array(list(cat_counts.values()))
        mu, sigma = float(np.mean(counts)), float(np.std(counts))
        cat_data = [
            {"category": c, "shortage_count": n, "z_score": round((n - mu) / sigma, 2),
             "is_anomaly": abs((n - mu) / sigma) > 1.5}
            for c, n in cat_counts.most_common()
        ]

    df_cat = pd.DataFrame(cat_data)

    # Anomaly alert cards
    anomalies = df_cat[df_cat["is_anomaly"] == True] if "is_anomaly" in df_cat.columns else df_cat[df_cat["is_anomaly"] == "yes"]

    if len(anomalies) > 0:
        st.markdown("#### 🚨 Anomalous Categories Detected")
        acols = st.columns(len(anomalies))
        for i, (_, row) in enumerate(anomalies.iterrows()):
            with acols[i]:
                cat_name = row["category"]
                z = row["z_score"]
                count = row["shortage_count"]
                st.error(f"**{cat_name}**  \nz = {z}  \n{count} shortage records")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Shortage Volume by Category")
        fig, ax = plt.subplots(figsize=(7, 8))
        ax.set_facecolor("#0e1117")
        fig.patch.set_facecolor("#0e1117")

        cats = df_cat["category"].tolist()
        counts_list = df_cat["shortage_count"].tolist()
        is_anom = df_cat["is_anomaly"].tolist()
        colors = ["#ef4444" if a else "#3b82f6" for a in is_anom]

        ax.barh(range(len(cats)), counts_list, color=colors, edgecolor="#1e2d4a", height=0.6)
        ax.set_yticks(range(len(cats)))
        ax.set_yticklabels(cats, color="#8899b4", fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Shortage Count", color="#8899b4", fontsize=9)
        ax.tick_params(colors="#8899b4", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#1e2d4a")
        ax.spines["bottom"].set_color("#1e2d4a")
        st.pyplot(fig)

    with col2:
        st.markdown("#### Z-Score Distribution")
        fig, ax = plt.subplots(figsize=(7, 8))
        ax.set_facecolor("#0e1117")
        fig.patch.set_facecolor("#0e1117")

        z_scores = df_cat["z_score"].tolist()
        ax.barh(range(len(cats)), z_scores, color=colors, edgecolor="#1e2d4a", height=0.6)
        ax.set_yticks(range(len(cats)))
        ax.set_yticklabels(cats, color="#8899b4", fontsize=8)
        ax.invert_yaxis()
        ax.axvline(x=1.5, color="#ef4444", linestyle="--", alpha=0.5, linewidth=1)
        ax.axvline(x=-1.5, color="#ef4444", linestyle="--", alpha=0.5, linewidth=1)
        ax.set_xlabel("Z-Score", color="#8899b4", fontsize=9)
        ax.tick_params(colors="#8899b4", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#1e2d4a")
        ax.spines["bottom"].set_color("#1e2d4a")
        st.pyplot(fig)


# ─── VIEW: TIME SERIES ──────────────────────────────────

elif view == "◇ Time Series":
    st.markdown("### Time-Series Analysis")
    st.markdown("Shortage volume trends over time")

    # Aggregate by year
    yearly = df_records[df_records["posting_year"].notna()].groupby("posting_year").size().reset_index(name="count")
    yearly["posting_year"] = yearly["posting_year"].astype(int)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_facecolor("#0e1117")
    fig.patch.set_facecolor("#0e1117")

    ax.fill_between(yearly["posting_year"], yearly["count"], alpha=0.3, color="#3b82f6")
    ax.plot(yearly["posting_year"], yearly["count"], color="#3b82f6", linewidth=2.5, marker="o", markersize=6)

    ax.set_xlabel("Year", color="#8899b4", fontsize=10)
    ax.set_ylabel("New Shortage Records", color="#8899b4", fontsize=10)
    ax.set_title("Annual Shortage Volume", color="white", fontsize=12, pad=10)
    ax.tick_params(colors="#8899b4", labelsize=9)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#1e2d4a")
    ax.spines["bottom"].set_color("#1e2d4a")
    ax.grid(axis="y", color="#1e2d4a", linewidth=0.5, alpha=0.5)
    st.pyplot(fig)

    # Monthly by reason (stacked area)
    st.markdown("#### Monthly Shortage Volume by Reason")

    monthly = df_records[df_records["posting_year"].notna()].copy()
    monthly["period"] = monthly["posting_year"].astype(int).astype(str) + "-" + monthly["posting_month"].astype(int).apply(lambda x: f"{x:02d}")

    monthly_pivot = monthly.groupby(["period", "shortage_reason"]).size().unstack(fill_value=0)
    monthly_pivot = monthly_pivot.sort_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_facecolor("#0e1117")
    fig.patch.set_facecolor("#0e1117")

    reason_order = list(REASON_COLORS.keys())
    existing_reasons = [r for r in reason_order if r in monthly_pivot.columns]
    colors = [REASON_COLORS[r] for r in existing_reasons]

    monthly_pivot[existing_reasons].plot.area(ax=ax, stacked=True, color=colors, alpha=0.7, linewidth=0)

    ax.set_xlabel("Month", color="#8899b4", fontsize=9)
    ax.set_ylabel("Shortage Records", color="#8899b4", fontsize=9)
    ax.tick_params(colors="#8899b4", labelsize=7)
    ax.legend(fontsize=7, loc="upper left", facecolor="#0e1117", edgecolor="#1e2d4a", labelcolor="#8899b4")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#1e2d4a")
    ax.spines["bottom"].set_color("#1e2d4a")

    # Show every 12th tick
    ticks = ax.get_xticks()
    ax.set_xticks(ticks[::12] if len(ticks) > 24 else ticks[::6])
    plt.xticks(rotation=30)
    st.pyplot(fig)


# ─── VIEW: SUPPLIER RISK ────────────────────────────────

elif view == "□ Supplier Risk":
    st.markdown("### Supplier Concentration Risk")
    st.markdown("Single-source dependency creates fragility — fewer suppliers = higher disruption risk")

    company_counts = df_records["company_name"].value_counts().head(20)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor("#0e1117")
    fig.patch.set_facecolor("#0e1117")

    palette = sns.color_palette("husl", len(company_counts))
    ax.barh(range(len(company_counts)), company_counts.values, color=palette, edgecolor="#1e2d4a", height=0.6)
    ax.set_yticks(range(len(company_counts)))
    ax.set_yticklabels(company_counts.index, color="#8899b4", fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Shortage Records", color="#8899b4", fontsize=9)
    ax.set_title("Top 20 Companies by Shortage Involvement", color="white", fontsize=11, pad=10)
    ax.tick_params(colors="#8899b4", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#1e2d4a")
    ax.spines["bottom"].set_color("#1e2d4a")

    for i, val in enumerate(company_counts.values):
        ax.text(val + 2, i, str(val), va="center", color="#8899b4", fontsize=8)

    st.pyplot(fig)

    # Single-source risk
    st.markdown("#### Single-Source Drugs (Highest Concentration Risk)")
    single_source = df_scores[df_scores["num_companies"] == 1].sort_values("risk_score", ascending=False)
    st.markdown(f"**{len(single_source)} drugs** with only one supplier in shortage records")

    if len(single_source) > 0:
        st.dataframe(
            single_source[["drug", "risk_score", "risk_level", "primary_category",
                           "current_status", "recurrence_count"]].head(20).rename(columns={
                "drug": "Drug", "risk_score": "Risk Score", "risk_level": "Level",
                "primary_category": "Category", "current_status": "Status",
                "recurrence_count": "Recurrence",
            }),
            use_container_width=True, hide_index=True,
        )


# ─── VIEW: METHODOLOGY ──────────────────────────────────

elif view == "◈ Methodology":
    st.markdown("### Risk Scoring Methodology")
    st.markdown("Transparent, reproducible composite scoring aligned with Exiger's SCRM framework")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Composite Risk Score Formula")
        st.code("""
Risk = 0.30 × Recurrence
     + 0.25 × Duration
     + 0.25 × CauseSeverity
     + 0.20 × StatusMultiplier

Scale: 0–100
        """)

        st.markdown("**Recurrence (30%)** — Normalized count of shortage events per drug.")
        st.markdown("**Duration (25%)** — Average days in shortage, normalized against max.")
        st.markdown("**Cause Severity (25%)** — Highest-severity cause observed.")
        st.markdown("**Status (20%)** — Active+unavailable=100, Active=80, Resolved=20.")

    with col2:
        st.markdown("#### Anomaly Detection")
        st.code("""
z = (count - μ) / σ
flag if |z| > 1.5
        """)
        st.markdown("Z-score analysis identifies therapeutic categories experiencing "
                     "statistically unusual shortage volumes.")

        st.markdown("#### Exiger Platform Parallel")
        st.markdown("""
This prototype mirrors Exiger's approach:
- **Map** supply chains → ETL pipeline from FDA API
- **Score** risk → Composite risk scoring engine
- **Detect** anomalies → Z-score analysis
- **Surface** intelligence → Interactive dashboard

The 1Exiger platform performs this at scale across 50,000+
pharmaceuticals with deep sub-tier visibility.
        """)

    st.markdown("---")
    st.markdown("#### Data Pipeline")
    st.markdown(f"""
| Component | Detail |
|-----------|--------|
| Source | FDA Drug Shortages API (`api.fda.gov/drug/shortages.json`) |
| Records | {len(cleaned_records):,} shortage events |
| Drugs | {len(drug_scores)} unique drugs scored |
| Companies | {len(set(r['company_name'] for r in cleaned_records))} suppliers |
| Processing | Python ETL → standardized reasons, computed durations |
| Storage | JSON / PostgreSQL |
| Visualization | Streamlit + matplotlib + seaborn |
    """)
