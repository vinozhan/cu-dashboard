import streamlit as st
import pandas as pd
import json
from db.database import engine, init_db
from etl.planning_importer import delete_latest_batch
from style import page_header

st.set_page_config(page_title="Planning Analysis", layout="wide")
init_db()

page_header(
    "Planning Analysis",
    "View latest upload status and analyze custom planning records by department and month.",
)


def _safe_json_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}

try:
    summary_sql = """
    SELECT d.name AS department, ub.source_month, COUNT(pr.id) AS records
    FROM planning_records pr
    JOIN departments d ON d.id = pr.department_id
    LEFT JOIN upload_batches ub ON ub.id = pr.batch_id
    GROUP BY d.name, ub.source_month
    ORDER BY d.name, ub.source_month
    """
    df_summary = pd.read_sql(summary_sql, engine)
except Exception:
    df_summary = pd.DataFrame()

if df_summary.empty:
    st.info("No planning records available yet. Configure fields and upload Excel first.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Total Records", int(df_summary["records"].sum()))
col2.metric("Departments", int(df_summary["department"].nunique()))
col3.metric("Months", int(df_summary["source_month"].fillna("Unknown").nunique()))

st.subheader("Record Count by Department and Month")
st.dataframe(df_summary, width="stretch", hide_index=True)

st.subheader("Latest Uploaded Records")
details_sql = """
SELECT
    d.name AS department,
    ub.file_name,
    ub.source_month,
    ub.uploaded_at,
    ub.total_rows,
    ub.valid_rows,
    ub.error_rows,
    ub.status
FROM upload_batches ub
JOIN departments d ON d.id = ub.department_id
ORDER BY ub.uploaded_at DESC
LIMIT 50
"""
df_batches = pd.read_sql(details_sql, engine)
st.dataframe(df_batches, width="stretch", hide_index=True)

if not df_batches.empty:
    st.markdown("### Manage Latest Upload")
    dept_options = ["All Departments"] + sorted(df_batches["department"].dropna().unique().tolist())
    selected_delete_dep = st.selectbox(
        "Delete latest batch for",
        dept_options,
        key="delete_latest_dep",
    )
    confirm_delete = st.checkbox(
        "I confirm deleting the latest uploaded batch",
        key="confirm_delete_latest",
    )
    if st.button("Delete Latest Upload", type="secondary", key="delete_latest_batch_btn"):
        if not confirm_delete:
            st.warning("Please confirm before deleting.")
        else:
            dep_id = None
            if selected_delete_dep != "All Departments":
                dep_id_sql = """
                SELECT id FROM departments WHERE name = :name LIMIT 1
                """
                dep_row = pd.read_sql(dep_id_sql, engine, params={"name": selected_delete_dep})
                if dep_row.empty:
                    st.error("Department not found.")
                    st.stop()
                dep_id = int(dep_row.iloc[0]["id"])
            result = delete_latest_batch(department_id=dep_id)
            if result["deleted"]:
                st.success(
                    f"Deleted batch #{result['batch_id']} with {result['deleted_rows']} records."
                )
                st.rerun()
            else:
                st.info(result["message"])

st.subheader("Data Explorer")
records_sql = """
SELECT
    d.name AS department,
    pr.source_month,
    pr.row_number,
    pr.data_json
FROM planning_records pr
JOIN departments d ON d.id = pr.department_id
ORDER BY pr.id DESC
LIMIT 1000
"""
df_records = pd.read_sql(records_sql, engine)

dep_options = ["All"] + sorted(df_records["department"].dropna().unique().tolist())
selected_dep = st.selectbox("Department", dep_options, index=0)

display_df = df_records.copy()
if selected_dep != "All":
    display_df = display_df[display_df["department"] == selected_dep]

safe_payload = display_df["data_json"].apply(_safe_json_dict)
expanded_data = pd.json_normalize(safe_payload)
flat_df = pd.concat(
    [
        display_df[["department", "source_month", "row_number"]].reset_index(drop=True),
        expanded_data.reset_index(drop=True),
    ],
    axis=1,
)
st.dataframe(flat_df, width="stretch", hide_index=True)
