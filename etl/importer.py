import pandas as pd
from datetime import datetime
from db.database import get_session, init_db
from db.models import Audit, ISOProject


def normalize_text(value):
    """Lowercase and strip whitespace for consistent matching."""
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def safe_str(value, default=""):
    """Safely convert any value to a stripped string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return str(value).strip()


def parse_date(value):
    """Parse date from various Excel formats."""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def import_audits(file_path_or_buffer, clear_existing=True):
    """
    Import 'All Audits 2026' workbook.
    Each sheet is a month (Jan 2026, Feb 2026, ...).
    """
    init_db()
    session = get_session()

    if clear_existing:
        session.query(Audit).delete()
        session.commit()

    xls = pd.ExcelFile(file_path_or_buffer)
    total_imported = 0

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Normalize column names: strip whitespace, lowercase
        df.columns = [c.strip() for c in df.columns]

        # Map columns flexibly
        col_map = _map_audit_columns(df.columns)
        if not col_map:
            continue  # skip sheets that don't match expected structure

        for _, row in df.iterrows():
            project_id = str(row.get(col_map.get("project_id", ""), "")).strip()
            if not project_id or project_id == "nan":
                continue

            audit = Audit(
                project_id=project_id,
                project_name=str(row.get(col_map.get("project", ""), "")).strip(),
                planning_start_date=parse_date(row.get(col_map.get("planning_start_date", ""))),
                planning_end_date=parse_date(row.get(col_map.get("planning_end_date", ""))),
                inspection_days=_safe_float(row.get(col_map.get("inspection_days", ""))),
                spg_name=str(row.get(col_map.get("spg_name", ""), "")).strip(),
                spg_status=str(row.get(col_map.get("spg_status", ""), "")).strip(),
                city=normalize_text(row.get(col_map.get("city", ""))),
                country=normalize_text(row.get(col_map.get("country", ""))),
                source_month=sheet_name,
            )
            session.add(audit)
            total_imported += 1

    session.commit()
    session.close()
    return total_imported


def import_iso_projects(file_path_or_buffer, clear_existing=True):
    """
    Import 'ISO Projects with Units' workbook.
    Each sheet is an ISO standard (ISO 9001, ISO 14001, ...).
    """
    init_db()
    session = get_session()

    if clear_existing:
        session.query(ISOProject).delete()
        session.commit()

    xls = pd.ExcelFile(file_path_or_buffer)
    total_imported = 0

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.columns = [c.strip() for c in df.columns]

        col_map = _map_iso_columns(df.columns)
        if not col_map:
            continue

        for _, row in df.iterrows():
            project_id = str(row.get(col_map.get("project_id", ""), "")).strip()
            if not project_id or project_id == "nan":
                continue

            iso_project = ISOProject(
                project_id=project_id,
                project_name=str(row.get(col_map.get("project_name", ""), "")).strip(),
                unit=str(row.get(col_map.get("unit", ""), "")).strip() if col_map.get("unit") else None,
                address=str(row.get(col_map.get("address", ""), "")).strip() if col_map.get("address") else None,
                postal_code=str(row.get(col_map.get("postal_code", ""), "")).strip() if col_map.get("postal_code") else None,
                city=normalize_text(row.get(col_map.get("city", ""))),
                state=str(row.get(col_map.get("state", ""), "")).strip() if col_map.get("state") else None,
                country=normalize_text(row.get(col_map.get("country", ""))),
                exp_date=parse_date(row.get(col_map.get("exp_date", ""))),
                iso_standard=sheet_name,
            )
            session.add(iso_project)
            total_imported += 1

    session.commit()
    session.close()
    return total_imported


def _map_audit_columns(columns):
    """Flexibly map audit Excel columns to our field names."""
    col_lower = {c.lower().replace(" ", "_").replace("-", "_"): c for c in columns}
    mapping = {}

    patterns = {
        "project_id": ["project_id", "projectid", "project_no"],
        "project": ["project", "project_name", "projectname"],
        "planning_start_date": ["planning_start_date", "start_date", "plan_start"],
        "planning_end_date": ["planning_end_date", "end_date", "plan_end"],
        "inspection_days": ["inspection_days", "inspectiondays", "days"],
        "spg_name": ["spg_name", "spg_name(iso_22000:2018)", "spgname"],
        "spg_status": ["spg_status", "spg_status(certified,_certification_suspended,_certification_withdrawn)", "spgstatus"],
        "city": ["city"],
        "country": ["country"],
    }

    for field, candidates in patterns.items():
        for candidate in candidates:
            if candidate in col_lower:
                mapping[field] = col_lower[candidate]
                break
        # Fallback: partial match
        if field not in mapping:
            for key, orig in col_lower.items():
                if field.split("_")[0] in key:
                    mapping[field] = orig
                    break

    # Must have at least project_id to be a valid sheet
    if "project_id" not in mapping:
        return None
    return mapping


def _map_iso_columns(columns):
    """Flexibly map ISO project Excel columns to our field names."""
    col_lower = {c.lower().replace(" ", "_").replace("-", "_"): c for c in columns}
    mapping = {}

    patterns = {
        "project_id": ["project_id", "projectid", "project_no"],
        "project_name": ["project_name", "projectname", "project"],
        "unit": ["unit", "unit(subsidiaries_of_project_name)"],
        "address": ["address_vc", "address", "addressvc"],
        "postal_code": ["postalcode_vc", "postal_code", "postalcodevc"],
        "city": ["city_vc", "city", "cityvc"],
        "state": ["state_vc", "state", "statevc"],
        "country": ["country_vc", "country", "countryvc"],
        "exp_date": ["exp_date", "expdate", "expiry_date", "expiry"],
    }

    for field, candidates in patterns.items():
        for candidate in candidates:
            if candidate in col_lower:
                mapping[field] = col_lower[candidate]
                break
        if field not in mapping:
            for key, orig in col_lower.items():
                if field.replace("_", "") in key.replace("_", ""):
                    mapping[field] = orig
                    break

    if "project_id" not in mapping:
        return None
    return mapping


def _safe_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
