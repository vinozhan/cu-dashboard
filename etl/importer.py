import pandas as pd
from datetime import datetime
from db.database import get_session, init_db
from db.models import Audit, ISOProject


def _is_na(value):
    """Check if a value is NA/NaN/None safely, without failing on datetime."""
    if value is None:
        return True
    try:
        return pd.isna(value)
    except (ValueError, TypeError):
        return False


def normalize_text(value):
    """Lowercase and strip whitespace for consistent matching."""
    if _is_na(value):
        return ""
    return str(value).strip().lower()


def safe_str(value, default=""):
    """Safely convert any value to a stripped string."""
    if _is_na(value):
        return default
    # Convert float IDs like 871338.0 to clean "871338"
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


def parse_date(value):
    """Parse date from various Excel formats."""
    if _is_na(value):
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

    import traceback as _tb

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Skip empty sheets
        if df.empty or len(df.columns) == 0:
            continue

        # Normalize column names: convert to string and strip whitespace
        df.columns = [str(c).strip() for c in df.columns]

        # Map columns flexibly
        col_map = _map_audit_columns(df.columns)
        if not col_map:
            continue  # skip sheets that don't match expected structure

        for row_idx, row in df.iterrows():
            try:
                project_id = safe_str(row.get(col_map.get("project_id", ""), ""))
                if not project_id or project_id == "nan":
                    continue

                audit = Audit(
                    project_id=project_id,
                    project_name=safe_str(row.get(col_map.get("project", ""), "")),
                    planning_start_date=parse_date(row.get(col_map.get("planning_start_date", ""))),
                    expiry_date=parse_date(row.get(col_map.get("expiry_date", ""))),
                    inspection_days=_safe_float(row.get(col_map.get("inspection_days", ""))),
                    inspection_type=safe_str(row.get(col_map.get("inspection_type", ""), "")),
                    spg_name=safe_str(row.get(col_map.get("spg_name", ""), "")),
                    spg_status=safe_str(row.get(col_map.get("spg_status", ""), "")),
                    city=normalize_text(row.get(col_map.get("city", ""))),
                    country=normalize_text(row.get(col_map.get("country", ""))),
                    source_month=sheet_name,
                )
                session.add(audit)
                total_imported += 1
            except Exception as e:
                # Build debug info for the failing row
                debug_info = {
                    "sheet": sheet_name,
                    "row_idx": row_idx,
                    "col_map": col_map,
                }
                for field, col_name in col_map.items():
                    val = row.get(col_name, "MISSING")
                    debug_info[f"{field} -> {col_name}"] = f"{type(val).__name__}: {repr(val)}"
                raise RuntimeError(
                    f"Error on sheet '{sheet_name}', row {row_idx}:\n"
                    + "\n".join(f"  {k}: {v}" for k, v in debug_info.items())
                    + f"\n\nOriginal error: {e}\n{_tb.format_exc()}"
                ) from e

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
        df.columns = [str(c).strip() for c in df.columns]

        col_map = _map_iso_columns(df.columns)
        if not col_map:
            continue

        # Forward-fill project-level fields for merged cell structure.
        # Project_ID, Project_Name, and Exp_Date appear once per project,
        # with subsequent rows blank for additional units.
        for field in ["project_id", "project_name", "exp_date"]:
            col_name = col_map.get(field)
            if col_name and col_name in df.columns:
                df[col_name] = df[col_name].ffill()

        for _, row in df.iterrows():
            project_id = safe_str(row.get(col_map.get("project_id", ""), ""))
            if not project_id or project_id == "nan":
                continue

            # Skip rows where unit-level fields are all empty (padding rows)
            unit_val = safe_str(row.get(col_map.get("unit", ""), ""))
            city_val = normalize_text(row.get(col_map.get("city", "")))
            exp_val = row.get(col_map.get("exp_date", ""))
            if not unit_val and not city_val and _is_na(exp_val):
                continue

            iso_project = ISOProject(
                project_id=project_id,
                project_name=safe_str(row.get(col_map.get("project_name", ""), "")),
                unit=unit_val if unit_val else None,
                address=safe_str(row.get(col_map.get("address", ""), "")) or None,
                postal_code=safe_str(row.get(col_map.get("postal_code", ""), "")) or None,
                city=city_val,
                state=safe_str(row.get(col_map.get("state", ""), "")) or None,
                country=normalize_text(row.get(col_map.get("country", ""))),
                exp_date=parse_date(exp_val),
                iso_standard=sheet_name,
            )
            session.add(iso_project)
            total_imported += 1

    session.commit()
    session.close()
    return total_imported


def _map_audit_columns(columns):
    """Flexibly map audit Excel columns to our field names."""
    # Exact match first (case-insensitive, stripped)
    col_exact = {c.strip().lower(): c for c in columns}
    mapping = {}

    # Exact column names: Project_ID, Project, Pl. St. Dt., Pl. End Dt.,
    # Insp. Days, Insp. Type, SPG. Name, SPG. Status, City, Country
    patterns = {
        "project_id": ["project_id"],
        "project": ["project", "project_name"],
        "planning_start_date": ["pl. st. dt.", "planning start date", "start_date"],
        "expiry_date": ["expiry date", "expiry_date", "exp_date", "exp. date"],
        "inspection_days": ["insp. days", "inspection_days", "inspection days"],
        "inspection_type": ["insp. type", "inspection_type", "inspection type"],
        "spg_name": ["spg. name", "spg_name", "spg name"],
        "spg_status": ["spg. status", "spg_status", "spg status"],
        "city": ["city"],
        "country": ["country"],
    }

    for field, candidates in patterns.items():
        for candidate in candidates:
            if candidate in col_exact:
                mapping[field] = col_exact[candidate]
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
    if _is_na(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
