import streamlit as st
import pandas as pd
from db.database import init_db, get_session
from etl.planning_importer import auto_create_fields_from_excel, import_planning_excel
from db.models import Department, FieldDefinition
from style import page_header
from sqlalchemy import text

st.set_page_config(page_title="Data Upload", layout="wide")
init_db()

page_header(
    "Data Upload",
    "Upload department Excel files. You can add departments and fields any time from Planning Config.",
)

st.divider()

# --- Upload: Department Planning Data ---
st.subheader("Department Excel Upload")
st.markdown("Choose any department and upload its Excel. New departments can be added from **Planning Config**.")

session = get_session()
departments = (
    session.query(Department)
    .filter(Department.is_active.is_(True))
    .order_by(Department.name.asc())
    .all()
)
active_fields = (
    session.query(FieldDefinition)
    .filter(FieldDefinition.is_active.is_(True))
    .order_by(FieldDefinition.id.asc())
    .all()
)
session.close()

if not departments:
    st.warning("No active departments found. Add a department in Planning Config first.")
else:
    dep_map = {f"{d.name} ({d.code})" if d.code else d.name: d.id for d in departments}
    selected_dep_label = st.selectbox("Select Department", list(dep_map.keys()), key="planning_department")
    planning_month = st.text_input("Source Month / Period", value="", placeholder="e.g. Apr 2026")
    planning_file = st.file_uploader(
        "Upload Department Planning Excel",
        type=["xlsx", "xls"],
        key="planning_upload",
    )
    if planning_file is not None:
        st.info(f"File: {planning_file.name} ({planning_file.size / 1024:.1f} KB)")
        auto_create = False
        if not active_fields:
            st.warning("No active custom fields found. You can auto-create fields from this Excel header.")
            auto_create = st.checkbox(
                "Auto-create fields from Excel columns for first upload",
                value=True,
                key="auto_create_fields",
            )
        else:
            st.markdown("**Expected columns (field_key or label):** " + ", ".join([f.field_key for f in active_fields]))

        if st.button("Import Planning Data", type="primary", key="import_planning"):
            with st.spinner("Importing planning records..."):
                try:
                    if not active_fields:
                        if not auto_create:
                            st.error("Enable auto-create fields, or add fields in Planning Config first.")
                            st.stop()
                        created = auto_create_fields_from_excel(planning_file)
                        planning_file.seek(0)
                        if created > 0:
                            st.success(f"Created {created} fields from Excel header.")

                    result = import_planning_excel(
                        planning_file,
                        department_id=dep_map[selected_dep_label],
                        source_month=planning_month.strip() or None,
                    )
                    st.success(
                        f"Batch #{result['batch_id']} imported from "
                        f"{result['sheets_imported']}/{result['sheets_total']} sheets. "
                        f"Rows: {result['valid_rows']}/{result['total_rows']} valid, "
                        f"errors: {result['error_rows']}."
                    )
                    if result["errors"]:
                        st.warning("Some rows were skipped due to validation errors.")
                        st.code("\n".join(result["errors"][:30]), language="text")
                    if result.get("sheet_stats"):
                        st.markdown("**Sheet Import Details**")
                        sheet_df = pd.DataFrame(result["sheet_stats"])
                        if not sheet_df.empty:
                            st.dataframe(sheet_df, width="stretch", hide_index=True)
                except Exception as e:
                    st.error(f"Planning import failed: {e}")

st.divider()

# --- Quick Data Status ---
st.subheader("Current Data Status")

try:
    session = get_session()
    planning_count = session.execute(text("SELECT COUNT(*) FROM planning_records")).scalar()
    planning_batches = session.execute(text("SELECT COUNT(*) FROM upload_batches")).scalar()
    department_count = session.execute(
        text("SELECT COUNT(*) FROM departments WHERE is_active = 1")
    ).scalar()
    session.close()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Active Departments", department_count or 0)

    with col2:
        st.metric("Planning Records", planning_count or 0)

    with col3:
        st.metric("Upload Batches", planning_batches or 0)
        
except Exception:
    st.info("No data imported yet.")
