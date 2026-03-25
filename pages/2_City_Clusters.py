import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from db.database import init_db
from etl.matcher import find_city_clusters
from style import page_header, style_plotly_fig, PLOTLY_COLORS

st.set_page_config(page_title="City Clusters", layout="wide")
init_db()

page_header(
    "City Clusters",
    "Group projects by city to identify travel optimization opportunities — visit multiple projects in one trip.",
)

# --- Sidebar Filters ---
st.sidebar.header("Filters")
min_projects = st.sidebar.slider(
    "Minimum projects per city",
    min_value=2,
    max_value=10,
    value=2,
)

try:
    city_summary, all_projects = find_city_clusters(min_projects=min_projects)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

if city_summary.empty:
    st.info("No city clusters found. Try lowering the minimum or upload data first.")
    st.stop()

# Country filter
countries = ["All"] + sorted(city_summary["country"].dropna().unique().tolist())
selected_country = st.sidebar.selectbox("Country", countries)

if selected_country != "All":
    city_summary = city_summary[city_summary["country"] == selected_country]
    all_projects = all_projects[all_projects["country"] == selected_country]

# --- KPI Cards ---
col1, col2, col3 = st.columns(3)
col1.metric("Cities with clusters", len(city_summary))
col2.metric("Total projects in clusters", city_summary["total_projects"].sum())
col3.metric("Top city project count", city_summary["total_projects"].max() if not city_summary.empty else 0)

st.divider()

# --- Bar Chart: Top Cities ---
st.subheader("Top Cities by Project Count")

fig_bar = px.bar(
    city_summary.head(20),
    x="city",
    y="total_projects",
    color="country",
    color_discrete_sequence=PLOTLY_COLORS,
    labels={"city": "City", "total_projects": "Projects", "country": "Country"},
    title="Cities with Most Auditable Projects",
)
fig_bar.update_layout(xaxis_tickangle=-45)
style_plotly_fig(fig_bar)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# --- Breakdown: Audits vs ISO per City ---
st.subheader("Audit vs ISO Expiry Breakdown by City")

breakdown_data = city_summary[["city", "country", "audit_count", "iso_count", "total_projects"]].copy()
breakdown_data.columns = ["City", "Country", "Audits", "ISO Expirations", "Total"]

st.dataframe(breakdown_data, use_container_width=True, hide_index=True)

st.divider()

# --- Drill-down: Select a city to see projects ---
st.subheader("City Detail View")

city_options = city_summary["city"].tolist()
if city_options:
    selected_city = st.selectbox("Select a city to view projects", city_options)

    city_projects = all_projects[all_projects["city"] == selected_city].copy()
    city_projects["relevant_date"] = pd.to_datetime(city_projects["relevant_date"])
    city_projects = city_projects.sort_values("relevant_date")

    display_cols = ["project_id", "project_name", "source_type", "detail", "relevant_date"]
    display_df = city_projects[display_cols].copy()
    display_df.columns = ["Project ID", "Project", "Type", "Standard/SPG", "Date"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Timeline for selected city
    if not city_projects.empty:
        timeline_data = []
        for _, row in city_projects.iterrows():
            end_date = row["relevant_date"] + pd.Timedelta(days=1)
            timeline_data.append({
                "Project": f"{row['project_id']} - {row['project_name']}",
                "Start": row["relevant_date"],
                "End": end_date,
                "Type": row["source_type"],
            })

        timeline_df = pd.DataFrame(timeline_data)
        fig_timeline = px.timeline(
            timeline_df,
            x_start="Start",
            x_end="End",
            y="Project",
            color="Type",
            color_discrete_sequence=PLOTLY_COLORS,
            title=f"Project Timeline in {selected_city.title()}",
        )
        fig_timeline.update_yaxes(autorange="reversed")
        style_plotly_fig(fig_timeline)
        st.plotly_chart(fig_timeline, use_container_width=True)

# --- Export ---
st.divider()
buffer = BytesIO()
city_summary.to_excel(buffer, index=False, engine="openpyxl")
st.download_button(
    label="Download City Summary as Excel",
    data=buffer.getvalue(),
    file_name="city_clusters.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
