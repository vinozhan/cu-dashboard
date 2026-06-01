import json
import re
from io import BytesIO
import streamlit as st
import pandas as pd
import plotly.express as px
from db.database import init_db, engine
from style import page_header, style_plotly_fig, PLOTLY_COLORS

st.set_page_config(page_title="City Clusters", layout="wide")
init_db()

page_header(
    "City Clusters",
    "Department-wise city concentration analysis for scalable planning and travel optimization.",
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


def _first_non_empty_series(df, columns):
    """Pick first non-empty value across candidate columns per row."""
    if not columns:
        return pd.Series([""] * len(df), index=df.index, dtype="object")
    cleaned = []
    for col in columns:
        if col not in df.columns:
            continue
        series = df[col].astype(str).str.strip()
        series = series.where(
            (~series.isna())
            & (series != "")
            & (~series.str.lower().isin(["nan", "none", "null"])),
            "",
        )
        cleaned.append(series)
    if not cleaned:
        return pd.Series([""] * len(df), index=df.index, dtype="object")
    merged = pd.concat(cleaned, axis=1).bfill(axis=1).iloc[:, 0]
    return merged.fillna("")


def _normalize_geo_text(value):
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()


def _most_frequent_non_empty(series, fallback="N/A"):
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA, "null": pd.NA})
        .dropna()
    )
    if cleaned.empty:
        return fallback
    return cleaned.value_counts().index[0]


@st.cache_data(show_spinner=False, ttl=20)
def _load_base_df(latest_only):
    if latest_only:
        records_sql = """
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
    else:
        records_sql = """
        SELECT
            d.name AS department,
            pr.source_month,
            pr.row_number,
            pr.data_json
        FROM planning_records pr
        JOIN departments d ON d.id = pr.department_id
        ORDER BY pr.id DESC
        """

    df = pd.read_sql(records_sql, engine)
    if df.empty:
        return df

    safe_payload = df["data_json"].apply(_safe_json_dict)
    expanded = pd.json_normalize(safe_payload)
    return pd.concat(
        [df[["department", "source_month", "row_number"]].reset_index(drop=True), expanded.reset_index(drop=True)],
        axis=1,
    )


@st.cache_data(show_spinner=False)
def _to_excel_bytes(df):
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


latest_only = st.toggle(
    "Use only latest upload per department",
    value=True,
    help="Recommended: avoids mixing old uploads with new files.",
)

base_df = _load_base_df(latest_only)
if base_df.empty:
    st.info("No planning records found. Upload department Excel files first.")
    st.stop()

all_dynamic_fields = [c for c in base_df.columns if c not in {"department", "source_month", "row_number"}]
city_field_candidates = [c for c in all_dynamic_fields if "city" in c.lower()]
country_field_candidates = [
    c for c in all_dynamic_fields
    if any(token in c.lower() for token in ["country", "nation", "cntry", "country_code", "countrycode"])
]

if not city_field_candidates:
    st.error("No city-like field found in planning data. Add a city column (e.g. city) in uploaded Excel.")
    st.stop()

st.subheader("Cluster Filters")
department_options = sorted(base_df["department"].dropna().unique().tolist())
fcol1, fcol2 = st.columns(2)

# Keep filter state in sync with new uploads:
# when a new department appears, include it automatically.
dep_state_key = "city_clusters_departments"
if dep_state_key not in st.session_state:
    st.session_state[dep_state_key] = department_options
else:
    current_selected = st.session_state.get(dep_state_key, [])
    valid_selected = [d for d in current_selected if d in department_options]
    new_departments = [d for d in department_options if d not in valid_selected]
    st.session_state[dep_state_key] = valid_selected + new_departments

selected_departments = fcol1.multiselect(
    "Departments",
    department_options,
    key=dep_state_key,
)
month_options = ["All"] + sorted(base_df["source_month"].dropna().unique().tolist())
selected_month = fcol2.selectbox("Source Month", month_options, index=0)

fcol3, fcol4 = st.columns(2)
city_field_options = ["Auto (all city columns)"] + city_field_candidates
city_field = fcol3.selectbox("City Field", city_field_options, index=0)
default_country_idx = 0
country_field = fcol4.selectbox(
    "Country Field (optional)",
    ["Auto (all country columns)", "(none)"] + country_field_candidates,
    index=default_country_idx,
)

fcol5, fcol6 = st.columns(2)
min_records = fcol5.slider("Min records per city", min_value=1, max_value=25, value=2)
top_n = fcol6.slider("Top cities to display", min_value=5, max_value=50, value=20)
st.divider()

work_df = base_df.copy()
if selected_departments:
    work_df = work_df[work_df["department"].isin(selected_departments)]
if selected_month != "All":
    work_df = work_df[work_df["source_month"] == selected_month]

if city_field == "Auto (all city columns)":
    work_df["city"] = _first_non_empty_series(work_df, city_field_candidates)
else:
    work_df["city"] = work_df[city_field].astype(str).str.strip()
work_df = work_df[(work_df["city"].notna()) & (work_df["city"] != "") & (work_df["city"].str.lower() != "nan")]
if country_field == "Auto (all country columns)":
    work_df["country"] = _first_non_empty_series(work_df, country_field_candidates)
elif country_field != "(none)" and country_field in work_df.columns:
    work_df["country"] = work_df[country_field].astype(str).str.strip()
else:
    # Fallback: if city values are in format "City, Country", split and infer country.
    split_city = work_df["city"].str.split(",", n=1, expand=True)
    if split_city.shape[1] > 1:
        work_df["city"] = split_city[0].astype(str).str.strip()
        work_df["country"] = split_city[1].astype(str).str.strip()
    else:
        work_df["country"] = "N/A"

work_df["country"] = work_df["country"].replace({"": "N/A", "nan": "N/A", "None": "N/A", "null": "N/A"})

if work_df.empty:
    st.info("No records for selected filters.")
    st.stop()

work_df["city_key"] = work_df["city"].apply(_normalize_geo_text)
work_df["country_key"] = work_df["country"].apply(_normalize_geo_text)
work_df = work_df[work_df["city_key"] != ""]

city_stats = (
    work_df.groupby("city_key", dropna=False)
    .agg(
        total_records=("row_number", "count"),
        department_count=("department", "nunique"),
    )
    .reset_index()
)
city_labels = (
    work_df.groupby("city_key", dropna=False)
    .agg(
        city=("city", lambda s: _most_frequent_non_empty(s, fallback="Unknown")),
        country=("country", lambda s: _most_frequent_non_empty(s, fallback="N/A")),
    )
    .reset_index()
)
city_summary = (
    city_stats.merge(city_labels, on="city_key", how="left")
    .query("total_records >= @min_records")
    .sort_values("total_records", ascending=False)
)

if city_summary.empty:
    st.info("No city clusters matched selected threshold.")
    st.stop()

city_summary_top = city_summary.head(top_n)
work_top = work_df[work_df["city_key"].isin(city_summary_top["city_key"])]
dept_city = (
    work_top.groupby(["city_key", "department"], dropna=False)
    .size()
    .reset_index(name="records")
)
dept_city = dept_city.merge(city_summary_top[["city_key", "city"]], on="city_key", how="left")

col1, col2, col3 = st.columns(3)
col1.metric("Cluster Cities", int(city_summary["city_key"].nunique()))
col2.metric("Records in Clusters", int(city_summary["total_records"].sum()))
col3.metric("Departments Covered", int(work_top["department"].nunique()))

st.divider()
st.subheader("Top City Clusters by Record Volume")
fig_bar = px.bar(
    city_summary_top,
    x="city",
    y="total_records",
    color="country",
    color_discrete_sequence=PLOTLY_COLORS,
    labels={"city": "City", "total_records": "Records", "country": "Country"},
)
fig_bar.update_layout(xaxis_tickangle=-35)
style_plotly_fig(fig_bar)
st.plotly_chart(fig_bar, width="stretch")

st.subheader("Department Contribution by City")
fig_stack = px.bar(
    dept_city.sort_values(["city", "records"], ascending=[True, False]),
    x="city",
    y="records",
    color="department",
    labels={"city": "City", "records": "Records", "department": "Department"},
)
fig_stack.update_layout(barmode="stack", xaxis_tickangle=-35)
style_plotly_fig(fig_stack)
st.plotly_chart(fig_stack, width="stretch")

st.subheader("Cluster Detail Table")
table_df = city_summary_top.copy()
table_df = table_df[["city", "country", "total_records", "department_count"]]
table_df.columns = ["City", "Country", "Total Records", "Department Count"]
st.dataframe(table_df, width="stretch", hide_index=True)

st.divider()
st.download_button(
    label="Download City Cluster Summary",
    data=_to_excel_bytes(city_summary),
    file_name="planning_city_clusters.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
