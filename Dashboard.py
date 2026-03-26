import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db.database import init_db
from etl.matcher import get_summary_stats, get_dashboard_data
from style import page_header, style_plotly_fig, PLOTLY_COLORS

st.set_page_config(
    page_title="Audit Dashboard",
    layout="wide",
)

init_db()

page_header(
    "Audit Optimization Dashboard",
    "Compare Food and System project expiries side-by-side. Identify overlap opportunities and optimize travel.",
)

# --- KPI Row ---
try:
    stats = get_summary_stats()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Food Projects", stats["total_audits"])
    col2.metric("System Projects", stats["total_iso_projects"])
    col3.metric("Overlaps (30d)", stats["overlaps_30_days"])
    col4.metric("Overlaps (60d)", stats["overlaps_60_days"])
    #col5.metric("Cities (2+ projects)", stats["cities_with_multiple_projects"])

    has_data = stats["total_audits"] > 0 or stats["total_iso_projects"] > 0

except Exception as e:
    st.warning(f"Database not initialized or empty. Please upload data first. ({e})")
    has_data = False

if not has_data:
    st.info("No data imported yet. Go to **Data Upload** page to import your Excel files.")
    st.stop()

# --- Load chart data ---
try:
    data = get_dashboard_data()
except Exception:
    st.stop()

# ============================================================
# Row 1: Side-by-side — Food by Month vs System by Standard
# ============================================================
st.divider()
st.subheader("Planned Project Distribution")

col_food, col_system = st.columns(2)

with col_food:
    st.markdown("**Food Projects by Planned Month**")
    df_month = data["food_by_month"]
    if not df_month.empty:
        month_abbr_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_month["sort_key"] = df_month["source_month"].apply(
            lambda x: next((i for i, m in enumerate(month_abbr_order) if x.startswith(m)), 99)
        )
        df_month = df_month.sort_values("sort_key")

        fig_month = px.bar(
            df_month, x="source_month", y="count",
            color_discrete_sequence=[PLOTLY_COLORS[1]],
            labels={"source_month": "Month", "count": "Projects"},
        )
        fig_month.update_layout(showlegend=False, height=350)
        style_plotly_fig(fig_month)
        st.plotly_chart(fig_month, use_container_width=True)
    else:
        st.info("No Food project data.")

with col_system:
    st.markdown("**System Projects by Planned Month**")
    df_sys_month = data["system_by_month"]
    if not df_sys_month.empty:
        month_abbr_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_sys_month["sort_key"] = df_sys_month["source_month"].apply(
            lambda x: next((i for i, m in enumerate(month_abbr_order) if x.startswith(m)), 99)
        )
        df_sys_month = df_sys_month.sort_values("sort_key")

        fig_sys_month = px.bar(
            df_sys_month, x="source_month", y="count",
            color_discrete_sequence=[PLOTLY_COLORS[0]],
            labels={"source_month": "Month", "count": "Projects"},
        )
        fig_sys_month.update_layout(showlegend=False, height=350)
        style_plotly_fig(fig_sys_month)
        st.plotly_chart(fig_sys_month, use_container_width=True)
    else:
        st.info("No System project data.")

# ============================================================
# Row 2: SPG Status (Food) vs System by Standard
# ============================================================
st.divider()
st.subheader("Status Overview")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Food Projects — SPG Status**")
    df_status = data["food_by_status"]
    if not df_status.empty:
        fig_status = px.pie(
            df_status, values="count", names="spg_status",
            color_discrete_sequence=PLOTLY_COLORS, hole=0.45,
        )
        fig_status.update_traces(
            textposition="inside",
            textinfo="percent+value",
            insidetextorientation="horizontal",
        )
        fig_status.update_layout(
            height=400, showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=11)),
            margin=dict(t=20, b=60),
        )
        style_plotly_fig(fig_status)
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No status data.")

with col_right:
    st.markdown("**System Projects by ISO Standard**")
    df_iso = data["system_by_standard"]
    if not df_iso.empty:
        fig_iso = px.bar(
            df_iso, x="iso_standard", y="count",
            color_discrete_sequence=[PLOTLY_COLORS[0]],
            labels={"iso_standard": "ISO Standard", "count": "Projects"},
        )
        fig_iso.update_layout(showlegend=False, height=400)
        style_plotly_fig(fig_iso)
        st.plotly_chart(fig_iso, use_container_width=True)
    else:
        st.info("No System project data.")

# ============================================================
# Row 3: Top Cities — Food vs System (full width)
# ============================================================
st.divider()
st.subheader("Top Cities — Food vs System")

df_combined = data["combined_cities"]
if not df_combined.empty:
    city_totals = df_combined.groupby("city")["count"].sum().nlargest(15).index
    df_top = df_combined[df_combined["city"].isin(city_totals)]

    fig_combined = px.bar(
        df_top, x="city", y="count", color="source",
        color_discrete_map={"Food": PLOTLY_COLORS[1], "System": PLOTLY_COLORS[0]},
        labels={"city": "City", "count": "Projects", "source": "Type"},
        barmode="group",
    )
    fig_combined.update_layout(
        height=450,
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    style_plotly_fig(fig_combined)
    st.plotly_chart(fig_combined, use_container_width=True)
else:
    st.info("No city data.")

# ============================================================
# Row 3: Upcoming Expiries — Side by Side
# ============================================================
st.divider()
st.subheader("Top 10 Upcoming Expiries")

col_food_exp, col_sys_exp = st.columns(2)

with col_food_exp:
    st.markdown("**Food Projects — Next Expiring**")
    df_food_up = data["food_upcoming"]
    if not df_food_up.empty:
        display_food = df_food_up.copy()
        display_food.columns = ["Project ID", "Project", "Expiry Date", "SPG Name", "City", "Country"]
        st.dataframe(display_food, use_container_width=True, hide_index=True, height=350)
    else:
        st.info("No upcoming Food expiries.")

with col_sys_exp:
    st.markdown("**System Projects — Next Expiring**")
    df_sys_up = data["system_upcoming"]
    if not df_sys_up.empty:
        display_sys = df_sys_up.copy()
        display_sys.columns = ["Project ID", "Project", "Expiry Date", "ISO Standard", "City", "Country"]
        st.dataframe(display_sys, use_container_width=True, hide_index=True, height=350)
    else:
        st.info("No upcoming System expiries.")
