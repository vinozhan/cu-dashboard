import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from db.database import init_db
from etl.matcher import find_overlaps
from style import page_header, style_plotly_fig, PLOTLY_COLORS

st.set_page_config(page_title="Audit Overlap Finder", layout="wide")
init_db()

page_header(
    "Audit Overlap Finder",
    "",
)

st.subheader("Filters")
colf1, colf2 = st.columns(2)

# Remove or set a very high default for the maximum gap filter
# If you want to completely remove the slider, comment out or remove the following lines:
# max_gap = colf1.slider("Maximum gap (days)", min_value=int(df["gap_days"].min()), max_value=int(df["gap_days"].max()), value=int(df["gap_days"].max()))
# filtered = df[df["gap_days"] <= max_gap]

# Instead, always show all overlaps:
filtered = df.copy()


# --- DEBUG: Show raw planning data and overlap matching details ---
try:
    df = find_overlaps()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Show debug info if no overlaps found
if df.empty:
    st.warning("No overlaps found. Showing all pairs with same Project ID or Project Name and their planned start date gap.")
    import pandas as pd
    from sqlalchemy import create_engine
    from db.database import DATABASE_URL
    engine = create_engine(DATABASE_URL)
    planning_raw = pd.read_sql(
        '''
        SELECT d.name AS department, pr.source_month, pr.data_json
        FROM planning_records pr
        JOIN departments d ON d.id = pr.department_id
        ''',
        engine,
    )
    planning_rows = []
    import re, json
    def _norm(value):
        if value is None:
            return ""
        text_val = str(value).strip().lower()
        text_val = re.sub(r"[^a-z0-9\s]", " ", text_val)
        text_val = re.sub(r"\s+", " ", text_val).strip()
        return "" if text_val in {"", "nan", "none"} else text_val
    for _, row in planning_raw.iterrows():
        payload = row["data_json"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        keys = {str(k).lower(): k for k in payload.keys()}
        def _pick(*candidates):
            for c in candidates:
                if c in keys:
                    return payload.get(keys[c])
            return None
        project_id = _pick("project_id", "projectid", "project_no", "project_number")
        project_name = _pick("project_name", "project", "name")
        planning_start_date = _pick(
            "planning_start_date", "planning_start", "start_date", "pl_st_dt", "pl__st__dt_",
        )
        city = _pick("city", "city_vc", "project_city")
        country = _pick("country", "country_vc", "project_country")
        planning_rows.append({
            "department": row["department"],
            "project_id": project_id,
            "project_name": project_name,
            "planning_start_date": planning_start_date,
            "city": city,
            "country": country,
            "norm_project_id": _norm(project_id),
            "norm_project_name": _norm(project_name),
        })
    planning_df = pd.DataFrame(planning_rows)
    planning_df["planning_start_date"] = pd.to_datetime(planning_df["planning_start_date"], errors="coerce")
    # DEBUG: Show normalization and date parsing for each record
    planning_df["month_year"] = planning_df["planning_start_date"].dt.to_period("M")
    st.write("[DEBUG] All planning records with normalization and month:", planning_df)
    pairs = []
    skipped = []
    n = len(planning_df)
    for i in range(n):
        for j in range(i+1, n):
            row1 = planning_df.iloc[i]
            row2 = planning_df.iloc[j]
            same_id = row1["norm_project_id"] and row1["norm_project_id"] == row2["norm_project_id"]
            same_name = row1["norm_project_name"] and row1["norm_project_name"] == row2["norm_project_name"]
            if same_id or same_name:
                date1 = row1["planning_start_date"]
                date2 = row2["planning_start_date"]
                # Only include if both dates are in the same month/year
                if pd.notna(date1) and pd.notna(date2):
                    if date1.to_period("M") == date2.to_period("M"):
                        gap = abs((date1 - date2).days)
                        pairs.append({
                            "Department 1": row1["department"],
                            "Department 2": row2["department"],
                            "Project ID 1": row1["project_id"],
                            "Project ID 2": row2["project_id"],
                            "Project Name 1": row1["project_name"],
                            "Project Name 2": row2["project_name"],
                            "Planned Start 1": date1,
                            "Planned Start 2": date2,
                            "Gap (days)": gap
                        })
                    else:
                        skipped.append(f"Pair skipped: Same ID/Name but different months: {date1} vs {date2}")
                else:
                    skipped.append(f"Pair skipped: Invalid date(s): {date1} vs {date2}")
    if skipped:
        st.write("[DEBUG] Skipped pairs:", skipped)
    if pairs:
        st.dataframe(pd.DataFrame(pairs))
    else:
        st.info("No pairs found with same Project ID or Name.")
    st.stop()


dept_options = ["All"] + sorted(df["department"].dropna().astype(str).unique().tolist())
selected_dept = colf2.selectbox("Department", dept_options, index=0)

# Apply department filter only
if selected_dept != "All":
    filtered = filtered[
        (filtered["department"] == selected_dept) | (filtered["matched_department"] == selected_dept)
    ]

# --- KPI Cards ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Matches Found", len(filtered))
col2.metric("Unique Projects", pd.concat([filtered["project_id"], filtered["matched_project_id"]]).dropna().nunique())
col3.metric("Avg Gap (days)", f"{filtered['gap_days'].mean():.0f}" if not filtered.empty else "N/A")

st.divider()

# --- Timeline Chart ---
st.subheader("Timeline View")

if not filtered.empty:
    gantt_rows = []
    for _, row in filtered.iterrows():
        label = (
            f"{row['department']} ↔ {row['matched_department']} | "
            f"{row['project_id']} - {row['project_name']}"
        )
        planning_start = pd.to_datetime(row["planning_start_date"])
        matched_start = pd.to_datetime(row["matched_planning_start_date"])

        # Use short 1-day bars to show both departments' planning points.
        gantt_rows.append({
            "Project": label,
            "Start": planning_start,
            "Finish": planning_start + pd.Timedelta(days=1),
            "Type": "Department A",
            "Gap": row["gap_days"],
        })
        gantt_rows.append({
            "Project": label,
            "Start": matched_start,
            "Finish": matched_start + pd.Timedelta(days=1),
            "Type": "Department B",
            "Gap": row["gap_days"],
        })

    timeline_df = pd.DataFrame(gantt_rows)

    fig = px.timeline(
        timeline_df,
        x_start="Start",
        x_end="Finish",
        y="Project",
        color="Type",
        color_discrete_map={
            "Department A": PLOTLY_COLORS[1],
            "Department B": PLOTLY_COLORS[0],
        },
        hover_data={"Gap": True, "Start": "|%Y-%m-%d"},
    )
    fig.update_yaxes(autorange="reversed")

    # Draw a dotted connector between the two department planning dates.
    for _, row in filtered.iterrows():
        label = (
            f"{row['department']} ↔ {row['matched_department']} | "
            f"{row['project_id']} - {row['project_name']}"
        )
        fig.add_shape(
            type="line",
            x0=row["planning_start_date"], x1=row["matched_planning_start_date"],
            y0=label, y1=label,
            line=dict(color="rgba(186,176,172,0.6)", width=2, dash="dot"),
        )

    fig.update_layout(
        height=max(400, len(filtered) * 50),
        xaxis_title="Planning Start Date",
        yaxis_title="",
    )
    style_plotly_fig(fig)
    st.plotly_chart(fig, width="stretch")

st.divider()

# --- Data Table ---
st.subheader("Matched Projects")

display_cols = [
    "urgency_rank", "department", "matched_department", "source_type",
    "project_id", "matched_project_id", "project_name", "matched_project_name",
    "planning_start_date", "matched_planning_start_date", "gap_days",
    "match_type", "city", "matched_city", "country", "matched_country",
]
display_df = filtered[display_cols].copy()
display_df.columns = [
    "Urgency", "Department A", "Department B", "Source",
    "Project ID A", "Project ID B", "Project A", "Project B",
    "Planning Start A", "Planning Start B", "Gap (days)",
    "Match Type", "City A", "City B", "Country A", "Country B",
]

st.dataframe(display_df, width="stretch", hide_index=True)

# --- Export ---
st.divider()
buffer = BytesIO()
display_df.to_excel(buffer, index=False, engine="openpyxl")
st.download_button(
    label="Export to Excel",
    data=buffer.getvalue(),
    file_name="audit_overlaps.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
