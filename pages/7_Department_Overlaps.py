import json
import re
from datetime import datetime
from itertools import combinations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db.database import engine, init_db
from style import PLOTLY_COLORS, page_header, style_plotly_fig

st.set_page_config(page_title="Department Overlaps", layout="wide")
init_db()

page_header(
    "Department Overlaps",
    "Find month-wise matching project pairs across departments using project id or project name.",
)


PROJECT_ID_KEYS = (
    "project_id",
    "projectid",
    "project_no",
    "project_number",
)

PROJECT_NAME_KEYS = (
    "project_name",
    "project",
    "project_title",
)

PROGRAM_KEYS = (
    "program",
    "programme",
    "program_name",
    "programme_name",
)

# Priority order is important: always prefer the real planning start column first.
PLANNED_DATE_KEYS = (
    "pl_st_dt",
    "pl__st__dt",
    "pl_start_dt",
    "pl_st_date",
    "planning_start_date",
    "planned_date",
    "planning_date",
    "plan_date",
    "start_date",
)

EXPIRY_DATE_KEYS = (
    "expiry_date",
    "exp_date",
    "exp_dt",
    "end_date",
    "pl_end_dt",
)

PAIR_COLUMNS = [
    "planned_month",
    "planned_year_month",
    "project_a_planned_year_month",
    "department_a",
    "department_b",
    "project_id",
    "project_name",
    "program",
    "program_department_b",
    "project_a_planned_start_date",
    "project_b_planned_start_date",
    "department_b_planned_year_month",
    "planning_start_day_gap",
    "pair_count",
    "match_type",
]


def _normalize_key(value):
    raw = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip()).strip("_")
    # Make keys resilient to variants like "pl__st__dt" vs "pl_st_dt".
    return re.sub(r"_+", "_", raw)


def _normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null"}:
        return ""
    return " ".join(text.split())


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


def _safe_str(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def _extract_by_keys(payload, key_set):
    if not payload:
        return ""
    normalized = {_normalize_key(k): v for k, v in payload.items()}
    for key in key_set:
        if key in normalized:
            return _safe_str(normalized[key])
    return ""


def _extract_from_row(row_dict, key_set):
    normalized = {_normalize_key(k): v for k, v in row_dict.items()}
    for key in key_set:
        if key in normalized:
            return _safe_str(normalized[key])
    return ""


def _month_from_date(value):
    if not value:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%b %Y")

    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%b %Y")


def _parse_date_safe(value):
    """Parse dates safely, preserving ISO yyyy-mm-dd semantics."""
    if not value:
        return pd.NaT
    text = _safe_str(value)
    if not text:
        return pd.NaT
    # ISO date should never be interpreted with dayfirst=True.
    iso_like = re.match(r"^\d{4}-\d{2}-\d{2}$", text)
    if iso_like:
        parsed = pd.to_datetime(text, errors="coerce", format="%Y-%m-%d")
        if not pd.isna(parsed):
            return parsed
    # Common DB datetime format; parse directly to avoid repeated parser warnings.
    iso_datetime_like = re.match(
        r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?$",
        text,
    )
    if iso_datetime_like:
        text_norm = text.replace("T", " ")
        parsed = pd.to_datetime(text_norm, errors="coerce", format="%Y-%m-%d %H:%M:%S.%f")
        if pd.isna(parsed):
            parsed = pd.to_datetime(text_norm, errors="coerce", format="%Y-%m-%d %H:%M:%S")
        if not pd.isna(parsed):
            return parsed
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=False)
    return parsed


def _date_iso(value):
    if not value:
        return ""
    parsed = _parse_date_safe(value)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def _format_excel_like_date(value):
    if not value:
        return ""
    parsed = _parse_date_safe(value)
    if pd.isna(parsed):
        return _safe_str(value)
    return f"{parsed.day}-{parsed.strftime('%b-%Y')}"


def _build_timeline_rows(pairs_df):
    rows = []
    connector_rows = []
    for _, row in pairs_df.iterrows():
        row_dict = row.to_dict()
        project_name = _safe_str(row.get("project_name"))
        project_id = _safe_str(row.get("project_id"))
        program_name = (
            _extract_from_row(row_dict, PROGRAM_KEYS)
            or _safe_str(row.get("program_department_b"))
            or "N/A"
        )
        project_label = (
            f"{project_name} ({project_id})"
            if project_name and project_id
            else (project_name or project_id or "Unknown Project")
        )

        # Keep this slot-based extraction generic so future columns like
        # department_c / project_c_planned_start_date can be supported easily.
        slot_keys = sorted(
            {
                key.replace("department_", "")
                for key in row.index
                if isinstance(key, str) and key.startswith("department_")
            }
        )
        slot_windows = []
        for slot in slot_keys:
            dep_name = _safe_str(row.get(f"department_{slot}")) or f"Department {slot.upper()}"
            start_dt = _parse_date_safe(row.get(f"project_{slot}_planned_start_date"))
            end_dt = _parse_date_safe(row.get(f"project_{slot}_expiry_date"))
            if pd.isna(start_dt):
                continue
            finish_dt = end_dt if pd.notna(end_dt) and end_dt >= start_dt else start_dt + pd.Timedelta(days=1)
            slot_windows.append(
                {
                    "slot": slot,
                    "department": dep_name,
                    "start": start_dt,
                    "finish": finish_dt,
                    "expiry_text": end_dt.strftime("%Y-%m-%d") if pd.notna(end_dt) else "N/A",
                }
            )

        if not slot_windows:
            continue

        dep_pair_label = " ↔ ".join([w["department"] for w in slot_windows])
        timeline_row = f"{project_label} | {dep_pair_label}"

        for window in slot_windows:
            rows.append(
                {
                    "Project": project_label,
                    "Program": program_name,
                    "Department Pair": dep_pair_label,
                    "Window": window["department"],
                    "Start": window["start"],
                    "Finish": window["finish"],
                    "Planned Start": window["start"].strftime("%Y-%m-%d"),
                    "Expiry Date": window["expiry_text"],
                    "Timeline Row": timeline_row,
                }
            )

        # Draw a gap line for first two departments (A-B style pairing),
        # and label the day difference on the same row.
        if len(slot_windows) >= 2:
            start_a = slot_windows[0]["start"]
            start_b = slot_windows[1]["start"]
            gap_days = int(abs((start_a - start_b).days))
            connector_rows.append(
                {
                    "Timeline Row": timeline_row,
                    "Start A": start_a,
                    "Start B": start_b,
                    "Gap Label": f"{gap_days} days",
                    "Gap Mid": start_a + (start_b - start_a) / 2,
                }
            )

    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    timeline_df = pd.DataFrame(rows)
    connectors_df = pd.DataFrame(connector_rows)
    return timeline_df, connectors_df


def _month_key(value):
    if not value:
        return ""
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if not pd.isna(parsed):
        return parsed.strftime("%Y-%m")
    return _normalize_text(value)


def _day_gap(date_a, date_b):
    if not date_a or not date_b:
        return None
    dt_a = _parse_date_safe(date_a)
    dt_b = _parse_date_safe(date_b)
    if pd.isna(dt_a) or pd.isna(dt_b):
        return None
    return int(abs((dt_a - dt_b).days))


def _pick_best_row_pair(left_rows, right_rows):
    """Pick the most accurate pair: same month-year first, then closest day gap."""
    left_candidates = left_rows.to_dict("records")
    right_candidates = right_rows.to_dict("records")

    best = None
    for lrow in left_candidates:
        for rrow in right_candidates:
            ldate = lrow.get("planned_start_dt")
            rdate = rrow.get("planned_start_dt")
            if pd.isna(ldate):
                ldate = _parse_date_safe(lrow.get("planned_start_date_actual"))
            if pd.isna(rdate):
                rdate = _parse_date_safe(rrow.get("planned_start_date_actual"))
            if pd.isna(ldate) or pd.isna(rdate):
                continue
            lmonth = lrow.get("planned_start_month_key")
            rmonth = rrow.get("planned_start_month_key")
            gap = int(abs((ldate - rdate).days))

            # Priority: same month-year (0) then different month-year (1)
            month_priority = 0 if lmonth and rmonth and lmonth == rmonth else 1
            sort_key = (month_priority, gap)
            if best is None or sort_key < best["sort_key"]:
                best = {"sort_key": sort_key, "left": lrow, "right": rrow, "gap": gap}

    if best is None:
        return None, None, None
    return best["left"], best["right"], best["gap"]


def _resolve_month(source_month, payload):
    planned_date = _extract_by_keys(payload, PLANNED_DATE_KEYS)
    planned_month = _month_from_date(planned_date)
    if planned_month:
        return planned_month
    return _safe_str(source_month)


def _extract_planned_start_month(payload):
    planned_date = _extract_by_keys(payload, PLANNED_DATE_KEYS)
    return _month_from_date(planned_date), _month_key(planned_date)


def _build_base_table(flat_df):
    rows = []
    for _, row in flat_df.iterrows():
        row_dict = row.to_dict()
        source_month = _safe_str(row_dict.get("source_month", ""))
        project_id = _extract_from_row(row_dict, PROJECT_ID_KEYS)
        project_name = _extract_from_row(row_dict, PROJECT_NAME_KEYS)
        program = _extract_from_row(row_dict, PROGRAM_KEYS)
        planned_date_value = _extract_from_row(row_dict, PLANNED_DATE_KEYS)
        planned_start_dt = _parse_date_safe(planned_date_value)
        expiry_dt = _parse_date_safe(_extract_from_row(row_dict, EXPIRY_DATE_KEYS))

        planned_start_month_label = (
            planned_start_dt.strftime("%b %Y") if pd.notna(planned_start_dt) else ""
        )
        planned_start_month_key = (
            planned_start_dt.strftime("%Y-%m") if pd.notna(planned_start_dt) else ""
        )
        month_label = planned_start_month_label or source_month

        rows.append(
            {
                "department": _safe_str(row_dict.get("department", "")),
                "source_month": source_month,
                "row_number": row_dict.get("row_number"),
                "planned_month": month_label,
                "planned_month_key": _month_key(month_label),
                "planned_start_month": planned_start_month_label,
                "planned_start_month_key": planned_start_month_key,
                "planned_start_date_actual": (
                    planned_start_dt.strftime("%Y-%m-%d") if pd.notna(planned_start_dt) else ""
                ),
                "expiry_date_actual": (
                    expiry_dt.strftime("%Y-%m-%d") if pd.notna(expiry_dt) else ""
                ),
                "planned_start_dt": planned_start_dt,
                "project_id": project_id,
                "project_name": project_name,
                "program": program,
                "project_id_norm": _normalize_text(project_id),
                "project_name_norm": _normalize_text(project_name),
                "program_norm": _normalize_text(program),
            }
        )
    return pd.DataFrame(rows)


def _build_pairs_from_group(group_df, match_cols, match_basis):
    pairs = []
    grouped = group_df.groupby(match_cols, dropna=False)
    for group_key, bucket in grouped:
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        if any(not _safe_str(v) for v in group_key):
            continue

        dep_names = sorted([dep for dep in bucket["department"].dropna().unique().tolist() if dep])
        if len(dep_names) < 2:
            continue

        for left_dep, right_dep in combinations(dep_names, 2):
            left_rows = bucket[bucket["department"] == left_dep]
            right_rows = bucket[bucket["department"] == right_dep]
            if left_rows.empty or right_rows.empty:
                continue

            left_match_dict, right_match_dict, best_gap_days = _pick_best_row_pair(left_rows, right_rows)
            if best_gap_days is None:
                continue

            pair_count = int(min(len(left_rows), len(right_rows)))
            left_match = pd.Series(left_match_dict)
            right_match = pd.Series(right_match_dict)

            pairs.append(
                {
                    "planned_month": left_match["planned_month"],
                    "planned_year_month": left_match["planned_start_month_key"],
                    "project_a_planned_year_month": left_match["planned_start_month_key"],
                    "department_b_planned_year_month": right_match["planned_start_month_key"],
                    "department_a": left_dep,
                    "department_b": right_dep,
                    "project_id": left_match["project_id"] or right_match["project_id"],
                    "project_name": left_match["project_name"] or right_match["project_name"],
                    "program": left_match["program"] or right_match["program"],
                    "program_department_b": right_match["program"] or left_match["program"],
                    "project_a_planned_start_date": left_match["planned_start_date_actual"],
                    "project_b_planned_start_date": right_match["planned_start_date_actual"],
                    "project_a_expiry_date": left_match.get("expiry_date_actual", ""),
                    "project_b_expiry_date": right_match.get("expiry_date_actual", ""),
                    "planning_start_day_gap": best_gap_days,
                    "pair_count": pair_count,
                    "match_basis": match_basis,
                }
            )
    return pairs


def _get_data_signature():
    sql = """
    SELECT
        COALESCE(COUNT(*), 0) AS record_count,
        COALESCE(MAX(id), 0) AS max_record_id
    FROM planning_records
    """
    pr = pd.read_sql(sql, engine).iloc[0]
    return (int(pr["record_count"]), int(pr["max_record_id"]))


@st.cache_data(show_spinner=False, ttl=20)
def load_base_data(data_signature):
    # Same source/query pattern used in Planning Analysis -> Data Explorer.
    sql = """
    WITH latest_batches AS (
        SELECT id
        FROM (
            SELECT
                ub.id,
                ub.department_id,
                ROW_NUMBER() OVER (
                    PARTITION BY ub.department_id
                    ORDER BY ub.uploaded_at DESC, ub.id DESC
                ) AS rn
            FROM upload_batches ub
        ) ranked
        WHERE rn = 1
    )
    SELECT
        d.name AS department,
        pr.source_month,
        pr.row_number,
        pr.data_json
    FROM planning_records pr
    JOIN departments d ON d.id = pr.department_id
    JOIN latest_batches lb ON lb.id = pr.batch_id
    ORDER BY pr.id DESC
    """
    records_df = pd.read_sql(sql, engine)
    if records_df.empty:
        return pd.DataFrame()
    safe_payload = records_df["data_json"].apply(_safe_json_dict)
    expanded_data = pd.json_normalize(safe_payload)
    flat_df = pd.concat(
        [
            records_df[["department", "source_month", "row_number"]].reset_index(drop=True),
            expanded_data.reset_index(drop=True),
        ],
        axis=1,
    )
    return _build_base_table(flat_df)


@st.cache_data(show_spinner=False, ttl=20)
def load_pair_data(match_fields, match_mode="any", data_signature=(0, 0)):
    base_df = load_base_data(data_signature)
    if base_df.empty:
        return base_df, pd.DataFrame(columns=PAIR_COLUMNS)
    # Backward-safe: if cached/legacy dataframe shape is loaded, derive missing columns.
    if "planned_start_month_key" not in base_df.columns:
        if "planned_month_key" in base_df.columns:
            base_df["planned_start_month_key"] = base_df["planned_month_key"]
        else:
            base_df["planned_start_month_key"] = ""
    if "planned_start_month" not in base_df.columns:
        if "planned_month" in base_df.columns:
            base_df["planned_start_month"] = base_df["planned_month"]
        else:
            base_df["planned_start_month"] = ""

    criteria_map = {
        "project_id": ("project_id_norm", "project_id"),
        "project_name": ("project_name_norm", "project_name"),
        "program": ("program_norm", "program"),
        "planning_start": ("planned_start_date_actual", "planning_start"),
    }
    selected = [c for c in match_fields if c in criteria_map]
    if not selected:
        return base_df, pd.DataFrame(columns=PAIR_COLUMNS)

    selected_key_cols = [criteria_map[c][0] for c in selected]
    combined_pairs = []
    if match_mode == "all":
        working_df = base_df.copy()
        for col in selected_key_cols:
            working_df = working_df[working_df[col].fillna("").astype(str).str.strip() != ""]
        if working_df.empty:
            return base_df, pd.DataFrame(columns=PAIR_COLUMNS)
        match_label = "+".join(selected)
        combined_pairs = _build_pairs_from_group(working_df, selected_key_cols, match_label)
    else:
        # Flexible mode: match by any selected field, but treat planning_start
        # as a supporting constraint (not a standalone key) to avoid false pairs.
        has_planning_start = "planning_start" in selected
        primary_criteria = [c for c in selected if c != "planning_start"]

        # If user selected only planning_start, do not create loose date-only pairs.
        if not primary_criteria and has_planning_start:
            return base_df, pd.DataFrame(columns=PAIR_COLUMNS)

        for criterion in primary_criteria:
            key_cols = [criteria_map[criterion][0]]
            label_parts = [criterion]
            if has_planning_start:
                key_cols.append(criteria_map["planning_start"][0])
                label_parts.append("planning_start")

            working_df = base_df.copy()
            for col in key_cols:
                working_df = working_df[working_df[col].fillna("").astype(str).str.strip() != ""]
            if working_df.empty:
                continue
            combined_pairs.extend(
                _build_pairs_from_group(working_df, key_cols, "+".join(label_parts))
            )

    pairs_df = pd.DataFrame(combined_pairs)
    if pairs_df.empty:
        # Fallback for usability:
        # 1) If planning_start is selected with others, retry without planning_start.
        # 2) If only planning_start selected, retry with project_name.
        if match_mode == "any":
            retry_fields = []
            if "planning_start" in selected and len(selected) > 1:
                retry_fields = [f for f in selected if f != "planning_start"]
            elif selected == ["planning_start"]:
                retry_fields = ["project_name"]
            if retry_fields:
                return load_pair_data(tuple(retry_fields), match_mode=match_mode)
        return base_df, pd.DataFrame(columns=PAIR_COLUMNS)

    grouped = (
        pairs_df.groupby(
            [
                "planned_month",
                "planned_year_month",
                "project_a_planned_year_month",
                "department_a",
                "department_b",
                "project_id",
                "project_name",
                "program",
                "program_department_b",
                "project_a_planned_start_date",
                "project_b_planned_start_date",
                "project_a_expiry_date",
                "project_b_expiry_date",
                "department_b_planned_year_month",
                "planning_start_day_gap",
                "pair_count",
            ],
            as_index=False,
        )["match_basis"]
        .apply(lambda s: ", ".join(sorted(set(s))))
    )
    grouped = grouped.rename(columns={"match_basis": "match_type"})
    for col in PAIR_COLUMNS:
        if col not in grouped.columns:
            grouped[col] = ""
    grouped = grouped[PAIR_COLUMNS]
    grouped = grouped.sort_values(
        by=["planned_month", "department_a", "department_b", "project_id", "project_name"],
        ascending=[False, True, True, True, True],
    )
    return base_df, grouped


match_options = ["project_id", "project_name", "program", "planning_start"]
selected_match_fields = st.multiselect(
    "Match Using",
    match_options,
    default=["project_id", "project_name", "planning_start"],
)
match_mode_label = st.selectbox(
    "Match Logic",
    ["Any selected field (recommended)", "All selected fields (strict)"],
    index=0,
)
match_mode = "any" if "Any selected field" in match_mode_label else "all"

data_signature = _get_data_signature()
base_df, pairs_df = load_pair_data(
    tuple(selected_match_fields),
    match_mode=match_mode,
    data_signature=data_signature,
)

if base_df.empty:
    st.info("No planning data found yet. Upload department files first.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Departments", int(base_df["department"].nunique()))
col2.metric("Months", int(base_df["planned_month"].replace("", pd.NA).dropna().nunique()))
matching_pairs_metric = col3.empty()

st.subheader("Filter Overlaps")
all_months = sorted([m for m in base_df["planned_month"].dropna().unique().tolist() if m], reverse=True)
selected_month = st.selectbox("Planned Month", ["All"] + all_months, index=0)

dep_options = sorted([d for d in base_df["department"].dropna().unique().tolist() if d])
# Keep filter selection in sync with uploads:
# auto-include newly available departments.
dep_state_key = "overlap_departments_filter"
if dep_state_key not in st.session_state:
    st.session_state[dep_state_key] = dep_options
else:
    current_selected = st.session_state.get(dep_state_key, [])
    valid_selected = [d for d in current_selected if d in dep_options]
    new_departments = [d for d in dep_options if d not in valid_selected]
    st.session_state[dep_state_key] = valid_selected + new_departments

selected_departments = st.multiselect(
    "Departments",
    dep_options,
    key=dep_state_key,
    help="Select departments to compare matching pairs.",
)
department_filter_mode = st.selectbox(
    "Department Filter Mode",
    [
        "Any selected department involved",
        "Both departments must be selected",
    ],
    index=0,
    help="Use 'Any' to quickly compare one department against others.",
)
selected_primary_department = st.selectbox(
    "Primary Department (left column)",
    ["All"] + dep_options,
    index=0,
)

display_df = pairs_df.copy()
if selected_month != "All":
    if "planned_month" in display_df.columns:
        display_df = display_df[display_df["planned_month"] == selected_month]
if selected_departments and {"department_a", "department_b"}.issubset(display_df.columns):
    selected_set = set(selected_departments)
    if "Any selected department involved" in department_filter_mode:
        display_df = display_df[
            display_df["department_a"].isin(selected_set)
            | display_df["department_b"].isin(selected_set)
        ]
    else:
        display_df = display_df[
            display_df["department_a"].isin(selected_set)
            & display_df["department_b"].isin(selected_set)
        ]
else:
    display_df = display_df.iloc[0:0]
if selected_primary_department != "All" and "department_a" in display_df.columns:
    display_df = display_df[display_df["department_a"] == selected_primary_department]

# Auto-generated pair filter based on currently visible rows.
if {"department_a", "department_b"}.issubset(display_df.columns) and not display_df.empty:
    if st.toggle(
        "Filter by specific department pairs",
        value=False,
        help="Enable only when needed; keeping this off improves loading speed.",
    ):
        pair_labels = (
            display_df["department_a"].astype(str).str.strip()
            + " ↔ "
            + display_df["department_b"].astype(str).str.strip()
        )
        display_df = display_df.assign(_pair_label=pair_labels)
        pair_options = sorted(display_df["_pair_label"].dropna().unique().tolist())
        selected_pairs = st.multiselect(
            "Department Pairs",
            pair_options,
            default=pair_options,
            help="Filter the table to specific department-vs-department pairs.",
        )
        if selected_pairs:
            display_df = display_df[display_df["_pair_label"].isin(selected_pairs)]
        else:
            display_df = display_df.iloc[0:0]
        display_df = display_df.drop(columns=["_pair_label"], errors="ignore")

# Recompute day-gap before any gap filtering so table and chart use identical values.
if {
    "project_a_planned_start_date",
    "project_b_planned_start_date",
}.issubset(display_df.columns):
    gap_series = pd.to_numeric(display_df.get("planning_start_day_gap"), errors="coerce")
    if gap_series.isna().any():
        missing_mask = gap_series.isna()
        recomputed = display_df.loc[missing_mask].apply(
            lambda r: _day_gap(r.get("project_a_planned_start_date"), r.get("project_b_planned_start_date")),
            axis=1,
        )
        display_df.loc[missing_mask, "planning_start_day_gap"] = recomputed

# Gap-based filter for both table and timeline.
if "planning_start_day_gap" in display_df.columns and not display_df.empty:
    gap_series = pd.to_numeric(display_df["planning_start_day_gap"], errors="coerce").dropna()
    if not gap_series.empty:
        min_gap = int(gap_series.min())
        max_gap = int(gap_series.max())
        if min_gap < max_gap:
            selected_gap_range = st.slider(
                "Gap Days Filter",
                min_value=min_gap,
                max_value=max_gap,
                value=(min_gap, max_gap),
                help="Show only department pairs whose planned start gap is within this range.",
            )
        else:
            selected_gap_range = (min_gap, max_gap)
            st.caption(f"Gap Days Filter fixed at {min_gap} day(s); all visible pairs have the same gap.")
        display_df = display_df[
            pd.to_numeric(display_df["planning_start_day_gap"], errors="coerce").between(
                selected_gap_range[0], selected_gap_range[1], inclusive="both"
            )
        ]

# Keep KPI synchronized with active filters.
matching_pairs_metric.metric("Matching Pairs", int(len(display_df)))

st.subheader("Department Matching Pairs")
if display_df.empty:
    st.warning("No matching pairs found for selected filters.")
else:
    full_row_count = len(display_df)
    max_table_rows = st.slider(
        "Rows to display",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100,
        help="Limit rendered rows for faster UI response on large datasets.",
    )
    # Single filtered source for both table and timeline chart.
    timeline_source_df = display_df.head(max_table_rows).copy()
    display_df = timeline_source_df.rename(
        columns={
            "program": "program_department_a",
        }
    )
    if "project_a_planned_start_date" in display_df.columns:
        display_df["project_a_planned_year_month"] = display_df["project_a_planned_start_date"].apply(
            _format_excel_like_date
        )
    if "project_b_planned_start_date" in display_df.columns:
        display_df["department_b_planned_year_month"] = display_df["project_b_planned_start_date"].apply(
            _format_excel_like_date
        )
    display_df = display_df.drop(
        columns=[
            "planned_month",
            "planned_year_month",
            "project_a_planned_start_date",
            "project_b_planned_start_date",
            "pair_count",
        ],
        errors="ignore",
    )
    st.dataframe(display_df, width="stretch", hide_index=True)
    if full_row_count > max_table_rows:
        st.caption("Showing limited rows for performance.")

    if st.toggle("Show Timeline Chart", value=False):
        st.subheader("Project Audit Timeline (Gantt)")
        timeline_limit = st.slider(
            "Timeline projects limit",
            min_value=50,
            max_value=2000,
            value=300,
            step=50,
            help="Lower values render faster.",
        )
        timeline_source_df = timeline_source_df.head(timeline_limit)
        timeline_df, connectors_df = _build_timeline_rows(timeline_source_df)
        if timeline_df.empty:
            st.info("No valid planned dates available for timeline chart.")
        else:
            fig = px.timeline(
                timeline_df,
                x_start="Start",
                x_end="Finish",
                y="Timeline Row",
                color="Window",
                hover_name="Project",
                hover_data={
                    "Program": True,
                    "Department Pair": True,
                    "Planned Start": True,
                    "Expiry Date": True,
                    "Start": False,
                    "Finish": False,
                    "Timeline Row": False,
                },
                color_discrete_sequence=PLOTLY_COLORS,
            )
            fig.update_yaxes(autorange="reversed", title_text="")
            fig.update_layout(
                xaxis_title="Date",
                legend_title_text="Department Window",
                height=max(420, min(1400, 40 * timeline_df["Timeline Row"].nunique())),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            if not connectors_df.empty:
                for _, c_row in connectors_df.iterrows():
                    fig.add_trace(
                        go.Scatter(
                            x=[c_row["Start A"], c_row["Start B"]],
                            y=[c_row["Timeline Row"], c_row["Timeline Row"]],
                            mode="lines",
                            line=dict(color="rgba(186,176,172,0.7)", width=2, dash="dot"),
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=[c_row["Gap Mid"]],
                            y=[c_row["Timeline Row"]],
                            mode="text",
                            text=[c_row["Gap Label"]],
                            textposition="top center",
                            textfont=dict(size=11, color="#5a6677"),
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )
            style_plotly_fig(fig)
            st.plotly_chart(fig, width="stretch")


