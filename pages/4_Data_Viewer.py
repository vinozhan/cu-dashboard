import streamlit as st
import pandas as pd
from io import BytesIO
from db.database import init_db, get_session, engine
from style import page_header
from sqlalchemy import text

st.set_page_config(page_title="Data Viewer", layout="wide")
init_db()

page_header(
    "Data Viewer",
    "Browse and filter all imported System Projects and Food Projects records.",
)

# --- Current Data Status ---
st.subheader("Current Data Status")

try:
    session = get_session()
    audit_count = session.execute(text("SELECT COUNT(*) FROM audits")).scalar() or 0
    iso_count = session.execute(text("SELECT COUNT(*) FROM iso_projects")).scalar() or 0
    audit_months = session.execute(text("SELECT DISTINCT source_month FROM audits")).fetchall()
    iso_standards = session.execute(text("SELECT DISTINCT iso_standard FROM iso_projects")).fetchall()
    session.close()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("System Projects Records", iso_count)
        if iso_standards:
            st.markdown("**Standards loaded:** " + ", ".join(sorted([r[0] for r in iso_standards])))
        
    with col2:
        st.metric("Food Projects Records", audit_count)
        if audit_months:
            st.markdown("**Months loaded:** " + ", ".join(sorted([r[0] for r in audit_months])))
except Exception:
    st.info("No data imported yet. Go to **Data Upload** to import.")

st.divider()

tab1, tab2 = st.tabs(["System Projects Data", "Food Projects Data"])

with tab1:
    try:
        df_iso = pd.read_sql("SELECT * FROM iso_projects", engine)
    except Exception:
        df_iso = pd.DataFrame()

    if df_iso.empty:
        st.info("No System Projects data imported yet. Go to **Data Upload** to import.")
    else:
        # Filters
        col_f1, col_f2 = st.columns(2)
        standards = ["All"] + sorted(df_iso["iso_standard"].dropna().unique().tolist())
        sel_std = col_f1.selectbox("Filter by ISO Standard", standards, key="iso_std_filter")

        iso_countries = ["All"] + sorted(df_iso["country"].dropna().unique().tolist())
        sel_iso_country = col_f2.selectbox("Filter by Country", iso_countries, key="iso_country_filter")

        display_iso = df_iso.copy()
        if sel_std != "All":
            display_iso = display_iso[display_iso["iso_standard"] == sel_std]
        if sel_iso_country != "All":
            display_iso = display_iso[display_iso["country"] == sel_iso_country]

        st.markdown(f"Showing **{len(display_iso)}** of {len(df_iso)} records")
        st.dataframe(
            display_iso.drop(columns=["id"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )

        # Export
        buffer = BytesIO()
        display_iso.drop(columns=["id"], errors="ignore").to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="Download Filtered System Projects",
            data=buffer.getvalue(),
            file_name="iso_projects_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_iso",
        )

with tab2:
    try:
        df_audits = pd.read_sql("SELECT * FROM audits", engine)
    except Exception:
        df_audits = pd.DataFrame()

    if df_audits.empty:
        st.info("No audit data imported yet. Go to **Data Upload** to import.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        months = ["All"] + sorted(df_audits["source_month"].dropna().unique().tolist())
        sel_month = col_f1.selectbox("Filter by Month", months, key="audit_month_filter")

        countries = ["All"] + sorted(df_audits["country"].dropna().unique().tolist())
        sel_country = col_f2.selectbox("Filter by Country", countries, key="audit_country_filter")

        statuses = ["All"] + sorted(df_audits["spg_status"].dropna().unique().tolist())
        sel_status = col_f3.selectbox("Filter by SPG Status", statuses, key="audit_status_filter")

        display = df_audits.copy()
        if sel_month != "All":
            display = display[display["source_month"] == sel_month]
        if sel_country != "All":
            display = display[display["country"] == sel_country]
        if sel_status != "All":
            display = display[display["spg_status"] == sel_status]

        st.markdown(f"Showing **{len(display)}** of {len(df_audits)} records")
        st.dataframe(
            display.drop(columns=["id"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )

        # Export
        buffer = BytesIO()
        display.drop(columns=["id"], errors="ignore").to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="Download Filtered Food Projects",
            data=buffer.getvalue(),
            file_name="audits_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_audits",
        )


