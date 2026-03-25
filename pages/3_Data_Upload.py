import streamlit as st
from db.database import init_db, get_session
from etl.importer import import_audits, import_iso_projects
from style import page_header
from sqlalchemy import text

st.set_page_config(page_title="Data Upload", layout="wide")
init_db()

page_header(
    "Data Upload",
    "Upload your Excel workbooks to import or refresh the dashboard data.",
)

# --- Upload: All System Projects ---
st.subheader("1. System Projects")
st.markdown("Excel workbook with ISO standard sheets (ISO 9001, ISO 14001, ...).")

iso_file = st.file_uploader(
    "Upload 'System Projects' workbook",
    type=["xlsx", "xls"],
    key="iso_upload",
)

if iso_file is not None:
    st.info(f"File: {iso_file.name} ({iso_file.size / 1024:.1f} KB)")

    col1, col2 = st.columns(2)
    clear_iso = col1.checkbox("Clear existing System project data before import", value=True, key="clear_iso")

    if col2.button("Import System Projects", type="primary", key="import_iso"):
        with st.spinner("Importing System project data..."):
            try:
                count = import_iso_projects(iso_file, clear_existing=clear_iso)
                st.success(f"Successfully imported {count} System project records.")
            except Exception as e:
                st.error(f"Import failed: {e}")
st.divider()

# --- Upload: Food Projects with Units ---
st.subheader("2. Food Projects")
st.markdown("Excel workbook with monthly sheets (e.g. Jan, Feb, ...).")

audit_file = st.file_uploader(
    "Upload 'Food Projects' workbook",
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

# --- Quick Data Status ---
st.subheader("Current Data Status")

try:
    session = get_session()
    audit_count = session.execute(text("SELECT COUNT(*) FROM audits")).scalar()
    iso_count = session.execute(text("SELECT COUNT(*) FROM iso_projects")).scalar()

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
    st.info("No data imported yet.")
