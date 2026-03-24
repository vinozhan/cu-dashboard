import streamlit as st
from db.database import init_db
from etl.matcher import get_summary_stats

st.set_page_config(
    page_title="Audit Dashboard",
    page_icon="📊",
    layout="wide",
)

init_db()

st.title("Audit Optimization Dashboard")
st.markdown("Combine audits with ISO certification renewals and optimize travel by city clustering.")

st.divider()

try:
    stats = get_summary_stats()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Audits", stats["total_audits"])
    col2.metric("ISO Projects", stats["total_iso_projects"])
    col3.metric("Overlaps (30d)", stats["overlaps_30_days"])
    col4.metric("Overlaps (60d)", stats["overlaps_60_days"])
    col5.metric("Cities (2+ projects)", stats["cities_with_multiple_projects"])

    if stats["total_audits"] == 0 and stats["total_iso_projects"] == 0:
        st.info("No data imported yet. Go to **Data Upload** page to import your Excel files.")

except Exception as e:
    st.warning(f"Database not initialized or empty. Please upload data first. ({e})")

st.divider()
st.markdown("### Pages")
st.markdown("""
- **Audit Overlap Finder** — Find projects where audit dates and ISO expiry dates are close enough to combine
- **City Clusters** — Group projects by city to optimize travel and reduce costs
- **Data Upload** — Import or refresh data from your Excel workbooks
""")
