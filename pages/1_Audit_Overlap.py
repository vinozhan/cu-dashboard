import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from db.database import init_db
from etl.matcher import find_overlaps

st.set_page_config(page_title="Audit Overlap Finder", layout="wide")
init_db()

st.title("Audit Overlap Finder")
st.markdown("Find projects where a planned audit and an ISO certification expiry fall within a short time window — so both can be done in one trip.")

st.divider()

# --- Sidebar Filters ---
st.sidebar.header("Filters")
max_gap = st.sidebar.slider(
    "Maximum gap (days)",
    min_value=7,
    max_value=180,
    value=60,
    step=7,
    help="Show matches where audit date and ISO expiry are within this many days",
)

try:
    df = find_overlaps(max_gap_days=max_gap)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

if df.empty:
    st.info("No overlaps found. Try increasing the gap window or upload data first.")
    st.stop()

# Additional filters based on loaded data
iso_standards = ["All"] + sorted(df["iso_standard"].dropna().unique().tolist())
selected_standard = st.sidebar.selectbox("ISO Standard", iso_standards)

countries = ["All"] + sorted(df["audit_country"].dropna().unique().tolist())
selected_country = st.sidebar.selectbox("Country", countries)

spg_statuses = ["All"] + sorted(df["spg_status"].dropna().unique().tolist())
selected_status = st.sidebar.selectbox("SPG Status", spg_statuses)

# Apply filters
filtered = df.copy()
if selected_standard != "All":
    filtered = filtered[filtered["iso_standard"] == selected_standard]
if selected_country != "All":
    filtered = filtered[filtered["audit_country"] == selected_country]
if selected_status != "All":
    filtered = filtered[filtered["spg_status"] == selected_status]

# --- KPI Cards ---
col1, col2, col3 = st.columns(3)
col1.metric("Matching Pairs", len(filtered))
col2.metric("Unique Projects", filtered["project_id"].nunique())
col3.metric("Avg Gap (days)", f"{filtered['abs_gap_days'].mean():.0f}" if not filtered.empty else "N/A")

st.divider()

# --- Timeline Chart ---
st.subheader("Timeline View")

if not filtered.empty:
    # Build timeline data: each project has an audit bar and an expiry marker
    timeline_data = []
    for _, row in filtered.iterrows():
        label = f"{row['project_id']} - {row['audit_project']}"
        # Audit period
        timeline_data.append({
            "Project": label,
            "Start": row["planning_start_date"],
            "End": row["planning_end_date"] if pd.notna(row["planning_end_date"]) else row["planning_start_date"],
            "Type": "Audit Period",
        })
        # ISO Expiry (show as a 1-day bar)
        timeline_data.append({
            "Project": label,
            "Start": row["exp_date"],
            "End": row["exp_date"] + pd.Timedelta(days=1),
            "Type": f"ISO Expiry ({row['iso_standard']})",
        })

    timeline_df = pd.DataFrame(timeline_data)
    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="End",
        y="Project",
        color="Type",
        title="Audit Periods vs ISO Expiry Dates",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(400, len(filtered) * 50))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Data Table ---
st.subheader("Matched Projects")

display_cols = [
    "project_id", "audit_project", "planning_start_date", "exp_date",
    "gap_days", "abs_gap_days", "iso_standard", "audit_city",
    "audit_country", "spg_name", "spg_status",
]
display_df = filtered[display_cols].copy()
display_df.columns = [
    "Project ID", "Project", "Audit Start", "ISO Expiry",
    "Gap (days)", "Abs Gap", "ISO Standard", "City",
    "Country", "SPG Name", "SPG Status",
]

st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- Export ---
st.divider()
buffer = BytesIO()
display_df.to_excel(buffer, index=False, engine="openpyxl")
st.download_button(
    label="Download as Excel",
    data=buffer.getvalue(),
    file_name="audit_overlaps.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
