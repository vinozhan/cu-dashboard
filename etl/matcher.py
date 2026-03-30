import pandas as pd
from sqlalchemy import text
from db.database import get_session, engine, _is_postgres


def _date_diff_days(col_a, col_b):
    """Return SQL expression for date difference in days (col_a - col_b)."""
    if _is_postgres:
        return f"({col_a}::date - {col_b}::date)"
    return f"(julianday({col_a}) - julianday({col_b}))"


def _abs_date_diff_days(col_a, col_b):
    """Return SQL expression for absolute date difference in days."""
    if _is_postgres:
        return f"ABS({col_a}::date - {col_b}::date)"
    return f"ABS(julianday({col_a}) - julianday({col_b}))"


def _current_date():
    """Return SQL for current date."""
    if _is_postgres:
        return "CURRENT_DATE"
    return "date('now')"


def _subquery_alias(alias):
    """PostgreSQL requires AS for subquery aliases, SQLite accepts both."""
    return f"AS {alias}"


def find_overlaps(max_gap_days=60):
    """
    Find projects where the audit's Expiry Date and an ISO project's
    Exp_Date fall within max_gap_days of each other.
    """
    diff_expr = _date_diff_days("a.expiry_date", "ip.exp_date")
    abs_diff_expr = _abs_date_diff_days("a.expiry_date", "ip.exp_date")

    query = text(f"""
        SELECT
            a.project_id,
            a.project_name AS audit_project,
            a.planning_start_date,
            a.expiry_date AS audit_expiry_date,
            a.inspection_days,
            a.spg_name,
            a.spg_status,
            a.city AS audit_city,
            a.country AS audit_country,
            a.source_month,
            ip.project_name AS iso_project,
            ip.unit,
            ip.city AS iso_city,
            ip.country AS iso_country,
            ip.exp_date AS iso_exp_date,
            ip.iso_standard,
            {diff_expr} AS gap_days
        FROM audits a
        INNER JOIN iso_projects ip
            ON a.project_id = ip.project_id
        WHERE a.expiry_date IS NOT NULL
            AND ip.exp_date IS NOT NULL
            AND {abs_diff_expr} <= :max_gap
        ORDER BY {abs_diff_expr}
    """)

    df = pd.read_sql(query, engine, params={"max_gap": max_gap_days})

    if not df.empty:
        df["gap_days"] = df["gap_days"].round(0).astype(int)
        df["abs_gap_days"] = df["gap_days"].abs()
        df["audit_expiry_date"] = pd.to_datetime(df["audit_expiry_date"])
        df["iso_exp_date"] = pd.to_datetime(df["iso_exp_date"])

    return df


def find_city_clusters(min_projects=2):
    """
    Group projects by city across both audits and ISO projects.
    Returns cities that have at least min_projects scheduled/expiring.
    """
    query_audits = text("""
        SELECT
            project_id,
            project_name,
            city,
            country,
            expiry_date AS relevant_date,
            'Food Expiry' AS source_type,
            spg_name AS detail,
            source_month
        FROM audits
        WHERE city IS NOT NULL AND city != ''
            AND expiry_date IS NOT NULL
    """)

    query_iso = text("""
        SELECT
            project_id,
            project_name,
            city,
            country,
            exp_date AS relevant_date,
            'System Expiry' AS source_type,
            iso_standard AS detail,
            NULL AS source_month
        FROM iso_projects
        WHERE city IS NOT NULL AND city != ''
    """)

    df_audits = pd.read_sql(query_audits, engine)
    df_iso = pd.read_sql(query_iso, engine)
    df_all = pd.concat([df_audits, df_iso], ignore_index=True)

    if df_all.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_all["relevant_date"] = pd.to_datetime(df_all["relevant_date"])

    # City summary: count of projects per city
    city_summary = (
        df_all.groupby(["city", "country"])
        .agg(
            total_projects=("project_id", "nunique"),
            food_count=("source_type", lambda x: (x == "Food Expiry").sum()),
            system_count=("source_type", lambda x: (x == "System Expiry").sum()),
            earliest_date=("relevant_date", "min"),
            latest_date=("relevant_date", "max"),
        )
        .reset_index()
    )

    city_summary = city_summary[city_summary["total_projects"] >= min_projects]
    city_summary = city_summary.sort_values("total_projects", ascending=False)

    return city_summary, df_all


def get_summary_stats():
    """Return high-level KPI stats for the home page."""
    abs_diff = _abs_date_diff_days("a.expiry_date", "ip.exp_date")

    session = get_session()
    try:
        total_audits = session.execute(text("SELECT COUNT(*) FROM audits")).scalar()
        total_iso = session.execute(text("SELECT COUNT(*) FROM iso_projects")).scalar()
        overlap_30 = session.execute(text(f"""
            SELECT COUNT(*) FROM audits a
            INNER JOIN iso_projects ip ON a.project_id = ip.project_id
            WHERE a.expiry_date IS NOT NULL
                AND ip.exp_date IS NOT NULL
                AND {abs_diff} <= 30
        """)).scalar()
        overlap_60 = session.execute(text(f"""
            SELECT COUNT(*) FROM audits a
            INNER JOIN iso_projects ip ON a.project_id = ip.project_id
            WHERE a.expiry_date IS NOT NULL
                AND ip.exp_date IS NOT NULL
                AND {abs_diff} <= 60
        """)).scalar()
        cities_with_multiple = session.execute(text(f"""
            SELECT COUNT(*) FROM (
                SELECT city FROM (
                    SELECT city FROM audits WHERE city IS NOT NULL AND city != '' AND expiry_date IS NOT NULL
                    UNION ALL
                    SELECT city FROM iso_projects WHERE city IS NOT NULL AND city != ''
                )
                {_subquery_alias('combined')}
                GROUP BY city
                HAVING COUNT(*) >= 2
            ) {_subquery_alias('cities')}
        """)).scalar()
    finally:
        session.close()

    return {
        "total_audits": total_audits or 0,
        "total_iso_projects": total_iso or 0,
        "overlaps_30_days": overlap_30 or 0,
        "overlaps_60_days": overlap_60 or 0,
        "cities_with_multiple_projects": cities_with_multiple or 0,
    }


def get_dashboard_data():
    """Return chart data for the dashboard home page."""
    cur_date = _current_date()

    # --- Food Projects (audits table) ---
    food_by_month = pd.read_sql(
        "SELECT source_month, COUNT(*) AS count FROM audits GROUP BY source_month",
        engine,
    )

    food_by_status = pd.read_sql(
        "SELECT spg_status, COUNT(*) AS count FROM audits WHERE spg_status IS NOT NULL AND spg_status != '' GROUP BY spg_status",
        engine,
    )

    food_top_cities = pd.read_sql(
        "SELECT city, country, COUNT(*) AS count FROM audits WHERE city IS NOT NULL AND city != '' GROUP BY city, country ORDER BY count DESC LIMIT 10",
        engine,
    )

    food_upcoming = pd.read_sql(
        text(f"SELECT project_id, project_name, expiry_date, spg_name, city, country FROM audits WHERE expiry_date IS NOT NULL AND expiry_date >= {cur_date} ORDER BY expiry_date LIMIT 10"),
        engine,
    )
    if not food_upcoming.empty:
        food_upcoming["expiry_date"] = pd.to_datetime(food_upcoming["expiry_date"])

    # --- System Projects (iso_projects table) ---
    # Planned start date = exp_date - 90 days, grouped by month.
    # Use pandas for date math to stay DB-agnostic.
    system_raw = pd.read_sql(
        "SELECT exp_date FROM iso_projects WHERE exp_date IS NOT NULL",
        engine,
    )
    if not system_raw.empty:
        system_raw["exp_date"] = pd.to_datetime(system_raw["exp_date"])
        system_raw["planned_date"] = system_raw["exp_date"] - pd.Timedelta(days=90)
        system_raw["source_month"] = system_raw["planned_date"].dt.strftime("%b %Y")
        system_by_month = system_raw.groupby("source_month").size().reset_index(name="count")
        # Add sort key for chronological ordering
        system_by_month["sort_date"] = pd.to_datetime(system_by_month["source_month"], format="%b %Y")
        system_by_month = system_by_month.sort_values("sort_date").drop(columns=["sort_date"])
    else:
        system_by_month = pd.DataFrame(columns=["source_month", "count"])

    system_by_standard = pd.read_sql(
        "SELECT iso_standard, COUNT(*) AS count FROM iso_projects GROUP BY iso_standard",
        engine,
    )

    system_top_cities = pd.read_sql(
        "SELECT city, country, COUNT(*) AS count FROM iso_projects WHERE city IS NOT NULL AND city != '' GROUP BY city, country ORDER BY count DESC LIMIT 10",
        engine,
    )

    system_upcoming = pd.read_sql(
        text(f"SELECT project_id, project_name, exp_date, iso_standard, city, country FROM iso_projects WHERE exp_date IS NOT NULL AND exp_date >= {cur_date} GROUP BY project_id, iso_standard, project_name, exp_date, city, country ORDER BY exp_date LIMIT 10"),
        engine,
    )
    if not system_upcoming.empty:
        system_upcoming["exp_date"] = pd.to_datetime(system_upcoming["exp_date"])

    # --- Combined: cities with both Food and System projects ---
    combined_cities = pd.read_sql(text(f"""
        SELECT city, country, source, COUNT(*) AS count FROM (
            SELECT city, country, 'Food' AS source FROM audits WHERE city IS NOT NULL AND city != '' AND expiry_date IS NOT NULL
            UNION ALL
            SELECT city, country, 'System' AS source FROM iso_projects WHERE city IS NOT NULL AND city != ''
        ) {_subquery_alias('combined')}
        GROUP BY city, country, source
        ORDER BY count DESC
    """), engine)

    return {
        "food_by_month": food_by_month,
        "food_by_status": food_by_status,
        "food_top_cities": food_top_cities,
        "food_upcoming": food_upcoming,
        "system_by_month": system_by_month,
        "system_by_standard": system_by_standard,
        "system_top_cities": system_top_cities,
        "system_upcoming": system_upcoming,
        "combined_cities": combined_cities,
    }
