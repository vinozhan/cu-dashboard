import streamlit as st
import pandas as pd
from db.database import get_session, init_db
from db.models import Department, FieldDefinition, PlanningRecord, UploadBatch
from style import page_header
from sqlalchemy.exc import IntegrityError

st.set_page_config(page_title="Planning Config", layout="wide")
init_db()

page_header(
    "Planning Configuration",
    "Add departments and custom fields used by the Excel planning uploader.",
)

tab_dep, tab_fields = st.tabs(["Departments", "Fields"])

with tab_dep:
    st.subheader("Departments")
    with st.form("add_department_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        dep_name = col1.text_input("Department Name")
        dep_code = col2.text_input("Department Code (optional)")
        save_dep = st.form_submit_button("Add Department", type="primary")

    if save_dep:
        if not dep_name.strip():
            st.error("Department name is required.")
        else:
            session = get_session()
            dep_name_clean = dep_name.strip()
            dep_code_clean = dep_code.strip() or None

            exists = session.query(Department).filter(Department.name == dep_name_clean).first()
            existing_code = None
            if dep_code_clean:
                existing_code = (
                    session.query(Department).filter(Department.code == dep_code_clean).first()
                )

            if exists:
                st.warning("Department already exists.")
            elif existing_code:
                st.warning(
                    f"Department code '{dep_code_clean}' is already used by '{existing_code.name}'."
                )
            else:
                session.add(Department(name=dep_name_clean, code=dep_code_clean))
                try:
                    session.commit()
                    st.success("Department added.")
                except IntegrityError:
                    session.rollback()
                    st.error(
                        "Department could not be added because the name or code already exists."
                    )
            session.close()

    session = get_session()
    deps = session.query(Department).order_by(Department.name.asc()).all()
    session.close()
    if deps:
        dep_rows = [{"id": d.id, "name": d.name, "code": d.code, "active": d.is_active} for d in deps]
        st.dataframe(pd.DataFrame(dep_rows), width="stretch", hide_index=True)

        st.markdown("### Manage Department")
        dep_options = {
            f"{d.name} ({d.code})" if d.code else d.name: d.id
            for d in deps
        }
        selected_dep_label = st.selectbox(
            "Select Department",
            list(dep_options.keys()),
            key="manage_department_select",
        )
        selected_dep_id = dep_options[selected_dep_label]

        confirm_action = st.checkbox(
            "I confirm this department action",
            key="confirm_department_action",
        )
        col_a, col_b, col_c = st.columns(3)

        if col_a.button("Set Active", key="set_dep_active"):
            if not confirm_action:
                st.warning("Please confirm the action first.")
            else:
                session = get_session()
                dep = session.query(Department).filter(Department.id == selected_dep_id).first()
                if dep:
                    dep.is_active = True
                    session.commit()
                    st.success(f"Department '{dep.name}' set to active.")
                session.close()
                st.rerun()

        if col_b.button("Set Inactive", key="set_dep_inactive"):
            if not confirm_action:
                st.warning("Please confirm the action first.")
            else:
                session = get_session()
                dep = session.query(Department).filter(Department.id == selected_dep_id).first()
                if dep:
                    dep.is_active = False
                    session.commit()
                    st.success(f"Department '{dep.name}' set to inactive.")
                session.close()
                st.rerun()

        if col_c.button("Delete Department", key="delete_department"):
            if not confirm_action:
                st.warning("Please confirm the action first.")
            else:
                session = get_session()
                dep = session.query(Department).filter(Department.id == selected_dep_id).first()
                if dep:
                    session.query(PlanningRecord).filter(
                        PlanningRecord.department_id == selected_dep_id
                    ).delete()
                    session.query(UploadBatch).filter(
                        UploadBatch.department_id == selected_dep_id
                    ).delete()
                    dep_name = dep.name
                    session.delete(dep)
                    session.commit()
                    st.success(f"Department '{dep_name}' and related data deleted.")
                session.close()
                st.rerun()
    else:
        st.info("No departments configured yet.")

with tab_fields:
    st.subheader("Custom Fields")
    with st.form("add_field_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        field_key = col1.text_input("Field Key (example: budget_amount)")
        label = col2.text_input("Label (example: Budget Amount)")
        col3, col4 = st.columns(2)
        data_type = col3.selectbox("Data Type", ["text", "number", "date", "boolean"], index=0)
        required = col4.checkbox("Required", value=False)
        save_field = st.form_submit_button("Add Field", type="primary")

    if save_field:
        if not field_key.strip() or not label.strip():
            st.error("Field key and label are required.")
        else:
            session = get_session()
            exists = session.query(FieldDefinition).filter(FieldDefinition.field_key == field_key.strip()).first()
            if exists:
                st.warning("Field key already exists.")
            else:
                session.add(
                    FieldDefinition(
                        field_key=field_key.strip(),
                        label=label.strip(),
                        data_type=data_type,
                        required=required,
                    )
                )
                session.commit()
                st.success("Field added.")
            session.close()

    session = get_session()
    fields = session.query(FieldDefinition).order_by(FieldDefinition.id.asc()).all()
    session.close()
    if fields:
        field_rows = [
            {
                "id": f.id,
                "field_key": f.field_key,
                "label": f.label,
                "data_type": f.data_type,
                "required": f.required,
                "active": f.is_active,
            }
            for f in fields
        ]
        st.dataframe(pd.DataFrame(field_rows), width="stretch", hide_index=True)
    else:
        st.info("No fields configured yet.")
