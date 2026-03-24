import streamlit as st
from db.database import init_db
from etl.importer import import_audits, import_iso_projects

st.set_page_config(page_title="Data Upload", layout="wide")
init_db()

st.title("Data Upload")
st.markdown("Upload your Excel workbooks to import or refresh the dashboard data.")

st.divider()

# --- Upload: All Audits 2026 ---
st.subheader("1. All Audits 2026")
st.markdown("Excel workbook with monthly sheets (Jan 2026, Feb 2026, ...).")

audit_file = st.file_uploader(
    "Upload 'All Audits 2026' workbook",
    type=["xlsx", "xls"],
    key="audit_upload",
)

if audit_file is not None:
    st.info(f"File: {audit_file.name} ({audit_file.size / 1024:.1f} KB)")

    col1, col2 = st.columns(2)
    clear_audits = col1.checkbox("Clear existing audit data before import", value=True, key="clear_audits")

    if col2.button("Import Audits", type="primary", key="import_audits"):
        with st.spinner("Importing audit data..."):
            try:
                count = import_audits(audit_file, clear_existing=clear_audits)
                st.success(f"Successfully imported {count} audit records.")
            except Exception as e:
                st.error(f"Import failed: {e}")
                import traceback
                st.code(traceback.format_exc(), language="text")

st.divider()

# --- Upload: ISO Projects with Units ---
st.subheader("2. ISO Projects with Units")
st.markdown("Excel workbook with ISO standard sheets (ISO 9001, ISO 14001, ...).")

iso_file = st.file_uploader(
    "Upload 'ISO Projects with Units' workbook",
    type=["xlsx", "xls"],
    key="iso_upload",
)

if iso_file is not None:
    st.info(f"File: {iso_file.name} ({iso_file.size / 1024:.1f} KB)")

    col1, col2 = st.columns(2)
    clear_iso = col1.checkbox("Clear existing ISO data before import", value=True, key="clear_iso")

    if col2.button("Import ISO Projects", type="primary", key="import_iso"):
        with st.spinner("Importing ISO project data..."):
            try:
                count = import_iso_projects(iso_file, clear_existing=clear_iso)
                st.success(f"Successfully imported {count} ISO project records.")
            except Exception as e:
                st.error(f"Import failed: {e}")

st.divider()

# --- Data Preview ---
st.subheader("Current Data Status")

from db.database import get_session
from sqlalchemy import text

try:
    session = get_session()
    audit_count = session.execute(text("SELECT COUNT(*) FROM audits")).scalar()
    iso_count = session.execute(text("SELECT COUNT(*) FROM iso_projects")).scalar()

    audit_months = session.execute(text("SELECT DISTINCT source_month FROM audits")).fetchall()
    iso_standards = session.execute(text("SELECT DISTINCT iso_standard FROM iso_projects")).fetchall()
    session.close()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Audit Records", audit_count)
        if audit_months:
            st.markdown("**Months loaded:** " + ", ".join(sorted([r[0] for r in audit_months])))

    with col2:
        st.metric("ISO Project Records", iso_count)
        if iso_standards:
            st.markdown("**Standards loaded:** " + ", ".join(sorted([r[0] for r in iso_standards])))

except Exception:
    st.info("No data imported yet.")

# --- Data Tables ---
st.divider()
st.subheader("Imported Data Viewer")

import pandas as pd
from db.database import engine

try:
    tab1, tab2 = st.tabs(["Audits Data", "ISO Projects Data"])

    with tab1:
        df_audits = pd.read_sql("SELECT * FROM audits", engine)
        if df_audits.empty:
            st.info("No audit data imported yet.")
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

    with tab2:
        df_iso = pd.read_sql("SELECT * FROM iso_projects", engine)
        if df_iso.empty:
            st.info("No ISO project data imported yet.")
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

except Exception:
    pass
