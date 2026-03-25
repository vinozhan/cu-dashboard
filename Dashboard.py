import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from db.database import init_db
from etl.matcher import get_summary_stats, get_dashboard_data
from style import page_header, style_plotly_fig, PLOTLY_COLORS

st.set_page_config(
    page_title="Audit Dashboard",
    #page_icon="https://img.icons8.com/fluency/48/audit.png"
    layout="wide",
)

init_db()

page_header(
    "Audit Optimization Dashboard",
    "Combine audits with ISO certification renewals and optimize travel by city clustering.",
)

# --- KPI Row ---
try:
    stats = get_summary_stats()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("System Projects", stats["total_iso_projects"])
    col2.metric("Food Projects", stats["total_audits"])
    col3.metric("Overlaps (30d)", stats["overlaps_30_days"])
    col4.metric("Overlaps (60d)", stats["overlaps_60_days"])
    col5.metric("Cities (2+ projects)", stats["cities_with_multiple_projects"])

    has_data = stats["total_audits"] > 0 or stats["total_iso_projects"] > 0

except Exception as e:
    st.warning(f"Database not initialized or empty. Please upload data first. ({e})")
    has_data = False

if not has_data:
    st.info("No data imported yet. Go to **Data Upload** page to import your Excel files.")
    st.stop()

col1, col2, col3 = st.columns(3) 

# with col1:                                                                                                                                                       
#     st.markdown("""                                                                                                                                              
#     #### Audit Overlap Finder                                                                                                                                    
#     Find projects where audit and ISO expiry dates are close enough to combine into one visit.                                                                   
#       """) 
# with col2:
#     st.markdown("""                                                                                                                                              
#     #### City Clusters                                                                                                                                          
#     Identify cities with multiple projects to optimize travel planning.                                                                                         
#     """)
# with col3:
#     st.markdown("""                                                                                                                                              
#     #### Data Viewer                                                                                                                                            
#     Browse and filter all imported audit and ISO project records.                                                                                                 
#      """)   

# --- Charts ---
try:
    data = get_dashboard_data()
except Exception:
    st.stop()

st.divider()

# Row 1: Audits by Month + SPG Status
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("System Projects by Month")
    df_month = data["audits_by_month"]
    if not df_month.empty:
        # Sort months chronologically — extract month abbreviation for ordering
        month_abbr_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df_month["sort_key"] = df_month["source_month"].apply(
            lambda x: next((i for i, m in enumerate(month_abbr_order) if x.startswith(m)), 99)
        )
        df_month = df_month.sort_values("sort_key")

        fig_month = px.bar(
            df_month,
            x="source_month",
            y="count",
            color_discrete_sequence=[PLOTLY_COLORS[0]],
            labels={"source_month": "Month", "count": "Audits"},
        )
        fig_month.update_layout(showlegend=False, height=350)
        style_plotly_fig(fig_month)
        st.plotly_chart(fig_month, use_container_width=True)
    else:
        st.info("No audit data available.")

with col_right:
    st.subheader("SPG Status Breakdown")
    df_status = data["audits_by_status"]
    if not df_status.empty:
        fig_status = px.pie(
            df_status,
            values="count",
            names="spg_status",
            color_discrete_sequence=PLOTLY_COLORS,
            hole=0.45,
        )
        fig_status.update_traces(
            textposition="inside",
            textinfo="percent+value",
            insidetextorientation="horizontal",
        )
        fig_status.update_layout(
            height=400,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
            ),
            margin=dict(t=20, b=60),
        )
        style_plotly_fig(fig_status)
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No status data available.")

st.divider()

# Row 2: Top Cities + Upcoming Expiries
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Top 10 Cities by System Count")
    df_cities = data["top_cities"]
    if not df_cities.empty:
        df_cities = df_cities.sort_values("count", ascending=True)
        fig_cities = px.bar(
            df_cities,
            x="count",
            y="city",
            orientation="h",
            color="country",
            color_discrete_sequence=PLOTLY_COLORS,
            labels={"city": "City", "count": "Audits", "country": "Country"},
        )
        fig_cities.update_layout(height=400, yaxis_title="")
        style_plotly_fig(fig_cities)
        st.plotly_chart(fig_cities, use_container_width=True)
    else:
        st.info("No city data available.")

with col_right2:
    st.subheader("Upcoming System Projects Expiries")
    df_upcoming = data["upcoming_expiries"]
    if not df_upcoming.empty:
        display_df = df_upcoming.copy()
        display_df.columns = ["Project ID", "Project", "Expiry Date", "SPG Name", "City", "Country"]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("No upcoming expiries found.")

# Row 3: ISO Standards Distribution
df_iso = data["iso_by_standard"]
if not df_iso.empty:
    st.divider()
    st.subheader("Food Projects by Standard")
    fig_iso = px.bar(
        df_iso,
        x="iso_standard",
        y="count",
        color="iso_standard",
        color_discrete_sequence=PLOTLY_COLORS,
        labels={"iso_standard": "ISO Standard", "count": "Projects"},
    )
    fig_iso.update_layout(showlegend=False, height=300)
    style_plotly_fig(fig_iso)
    st.plotly_chart(fig_iso, use_container_width=True)
