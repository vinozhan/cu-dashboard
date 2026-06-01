import pandas as pd
import re
from db.database import get_session, init_db
from db.models import Department, FieldDefinition, PlanningRecord, UploadBatch


def normalize_key(value: str) -> str:
    raw = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip()).strip("_")
    return re.sub(r"_+", "_", raw)


PLANNED_START_DATE_KEYS = {
    "pl_st_dt",
    "pl_start_dt",
    "pl_st_date",
    "planning_start_date",
    "planned_date",
    "planning_date",
}


def _to_bool(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _parse_date_value(value):
    """Parse date from mixed Excel formats into Excel-like d-Mon-YYYY."""
    def _format_excel_like(dt_value):
        return f"{dt_value.day}-{dt_value.strftime('%b-%Y')}"

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return _format_excel_like(value.date())

    # Excel numeric serial date (days since 1899-12-30).
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        parsed = pd.to_datetime(value, unit="D", origin="1899-12-30", errors="coerce")
        if not pd.isna(parsed):
            return _format_excel_like(parsed.date())

    raw = str(value).strip()
    if not raw:
        return None

    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        parsed = pd.to_datetime(raw, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return None
    return _format_excel_like(parsed.date())


def cast_value(value, data_type, field_key=None):
    if pd.isna(value):
        return None
    normalized_field_key = normalize_key(field_key or "")
    if normalized_field_key in PLANNED_START_DATE_KEYS:
        parsed = _parse_date_value(value)
        if parsed is not None:
            return parsed
    if data_type == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if data_type == "date":
        return _parse_date_value(value)
    if data_type == "boolean":
        return _to_bool(value)
    return str(value).strip()


def auto_create_fields_from_excel(file_path_or_buffer):
    """
    Bootstrap field definitions from Excel headers when no fields exist yet.
    Creates text fields with label=original header.
    """
    init_db()
    session = get_session()
    try:
        xls = pd.ExcelFile(file_path_or_buffer)
        created = 0
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, nrows=1)
            for col in df.columns:
                label = str(col).strip()
                field_key = normalize_key(label)
                if not field_key:
                    continue

                exists = (
                    session.query(FieldDefinition)
                    .filter(FieldDefinition.field_key == field_key)
                    .first()
                )
                if exists:
                    continue

                session.add(
                    FieldDefinition(
                        field_key=field_key,
                        label=label,
                        data_type="text",
                        required=False,
                        is_active=True,
                    )
                )
                created += 1

        session.commit()
        return created
    finally:
        session.close()


def import_planning_excel(file_path_or_buffer, department_id: int, source_month: str = None):
    init_db()
    session = get_session()
    errors = []

    department = session.query(Department).filter(Department.id == department_id, Department.is_active.is_(True)).first()
    if not department:
        session.close()
        raise ValueError("Selected department does not exist or is inactive.")

    fields = (
        session.query(FieldDefinition)
        .filter(FieldDefinition.is_active.is_(True))
        .order_by(FieldDefinition.id.asc())
        .all()
    )
    if not fields:
        session.close()
        raise ValueError("No active fields configured. Please add fields first.")

    field_map = {f.field_key: f for f in fields}
    label_to_key = {normalize_key(f.label): f.field_key for f in fields}
    key_to_key = {normalize_key(f.field_key): f.field_key for f in fields}

    xls = pd.ExcelFile(file_path_or_buffer)

    batch = UploadBatch(
        department_id=department_id,
        file_name=getattr(file_path_or_buffer, "name", "uploaded_file.xlsx"),
        source_month=source_month,
        total_rows=0,
        status="completed",
    )
    session.add(batch)
    session.flush()

    required_keys = [f.field_key for f in fields if f.required]
    total_rows = 0
    valid_rows = 0
    sheet_count_used = 0
    sheet_stats = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if df.empty:
            sheet_stats.append(
                {
                    "sheet_name": sheet_name,
                    "rows": 0,
                    "imported_rows": 0,
                    "status": "skipped",
                    "reason": "Sheet is empty",
                }
            )
            continue

        total_rows += len(df)
        excel_col_lookup = {}
        for col in df.columns:
            n_col = normalize_key(col)
            mapped_key = key_to_key.get(n_col) or label_to_key.get(n_col)
            if mapped_key:
                excel_col_lookup[mapped_key] = col

        missing_required_columns = [k for k in required_keys if k not in excel_col_lookup]
        if missing_required_columns:
            reason = f"Missing required columns: {', '.join(missing_required_columns)}"
            errors.append(
                f"Sheet '{sheet_name}': missing required columns - {', '.join(missing_required_columns)}"
            )
            sheet_stats.append(
                {
                    "sheet_name": sheet_name,
                    "rows": int(len(df)),
                    "imported_rows": 0,
                    "status": "skipped",
                    "reason": reason,
                }
            )
            continue

        sheet_count_used += 1
        row_source_month = source_month or sheet_name
        valid_rows_before_sheet = valid_rows
        for idx, row in df.iterrows():
            payload = {}
            row_has_error = False
            for field_key, field_def in field_map.items():
                source_col = excel_col_lookup.get(field_key)
                raw_value = row.get(source_col) if source_col else None
                casted = cast_value(raw_value, field_def.data_type, field_key=field_key)
                if field_def.required and (casted is None or casted == ""):
                    row_has_error = True
                    errors.append(f"Sheet '{sheet_name}' Row {idx + 2}: '{field_key}' is required.")
                payload[field_key] = casted

            if row_has_error:
                continue

            rec = PlanningRecord(
                batch_id=batch.id,
                department_id=department_id,
                row_number=idx + 2,
                source_month=row_source_month,
                data_json=payload,
            )
            session.add(rec)
            valid_rows += 1

        imported_rows = int(valid_rows - valid_rows_before_sheet)
        sheet_stats.append(
            {
                "sheet_name": sheet_name,
                "rows": int(len(df)),
                "imported_rows": imported_rows,
                "status": "imported" if imported_rows > 0 else "completed_with_no_valid_rows",
                "reason": "" if imported_rows > 0 else "All rows failed validation",
            }
        )

    if total_rows == 0:
        session.delete(batch)
        session.commit()
        session.close()
        raise ValueError("Uploaded workbook has no data rows in any sheet.")

    batch.total_rows = total_rows
    batch.valid_rows = valid_rows
    batch.error_rows = max(batch.total_rows - valid_rows, 0)
    if sheet_count_used == 0:
        batch.status = "failed"
    if batch.error_rows > 0:
        batch.status = "completed_with_errors"

    result = {
        "batch_id": batch.id,
        "sheets_total": len(xls.sheet_names),
        "sheets_imported": sheet_count_used,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "error_rows": batch.error_rows,
        "errors": errors[:100],
        "sheet_stats": sheet_stats,
    }
    session.commit()
    session.close()
    return result


def delete_latest_batch(department_id: int = None):
    init_db()
    session = get_session()
    try:
        query = session.query(UploadBatch)
        if department_id is not None:
            query = query.filter(UploadBatch.department_id == department_id)
        latest = query.order_by(UploadBatch.uploaded_at.desc(), UploadBatch.id.desc()).first()
        if not latest:
            return {"deleted": False, "message": "No upload batch found."}

        deleted_batch_id = latest.id
        deleted_rows = session.query(PlanningRecord).filter(PlanningRecord.batch_id == latest.id).delete()
        session.delete(latest)
        session.commit()
        return {
            "deleted": True,
            "batch_id": deleted_batch_id,
            "deleted_rows": deleted_rows,
        }
    finally:
        session.close()
