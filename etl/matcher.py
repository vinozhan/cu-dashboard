import pandas as pd
from sqlalchemy import text
from db.database import get_session, engine


def find_overlaps(max_gap_days=60):
    """
    Find projects where the audit's Expiry Date and an ISO project's
    Exp_Date fall within max_gap_days of each other.

    Returns a DataFrame with matched pairs and gap info.
    """
    query = text("""
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
            julianday(a.expiry_date) - julianday(ip.exp_date) AS gap_days
        FROM audits a
        INNER JOIN iso_projects ip
            ON a.project_id = ip.project_id
        WHERE a.expiry_date IS NOT NULL
            AND ip.exp_date IS NOT NULL
            AND ABS(julianday(a.expiry_date) - julianday(ip.exp_date)) <= :max_gap
        ORDER BY ABS(julianday(a.expiry_date) - julianday(ip.exp_date))
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
    session = get_session()
    try:
        total_audits = session.execute(text("SELECT COUNT(*) FROM audits")).scalar()
        total_iso = session.execute(text("SELECT COUNT(*) FROM iso_projects")).scalar()
        overlap_30 = session.execute(text("""
            SELECT COUNT(*) FROM audits a
            INNER JOIN iso_projects ip ON a.project_id = ip.project_id
            WHERE a.expiry_date IS NOT NULL
                AND ip.exp_date IS NOT NULL
                AND ABS(julianday(a.expiry_date) - julianday(ip.exp_date)) <= 30
        """)).scalar()
        overlap_60 = session.execute(text("""
            SELECT COUNT(*) FROM audits a
            INNER JOIN iso_projects ip ON a.project_id = ip.project_id
            WHERE a.expiry_date IS NOT NULL
                AND ip.exp_date IS NOT NULL
                AND ABS(julianday(a.expiry_date) - julianday(ip.exp_date)) <= 60
        """)).scalar()
        cities_with_multiple = session.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT city FROM (
                    SELECT city FROM audits WHERE city IS NOT NULL AND city != '' AND expiry_date IS NOT NULL
                    UNION ALL
                    SELECT city FROM iso_projects WHERE city IS NOT NULL AND city != ''
                )
                GROUP BY city
                HAVING COUNT(*) >= 2
            )
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
    audits_by_month = pd.read_sql(
        "SELECT source_month, COUNT(*) AS count FROM audits GROUP BY source_month",
        engine,
    )

    audits_by_status = pd.read_sql(
        "SELECT spg_status, COUNT(*) AS count FROM audits WHERE spg_status IS NOT NULL AND spg_status != '' GROUP BY spg_status",
        engine,
    )

    top_cities = pd.read_sql(
        "SELECT city, country, COUNT(*) AS count FROM audits WHERE city IS NOT NULL AND city != '' GROUP BY city, country ORDER BY count DESC LIMIT 10",
        engine,
    )

    upcoming_expiries = pd.read_sql(
        "SELECT project_id, project_name, expiry_date, spg_name, city, country FROM audits WHERE expiry_date IS NOT NULL AND expiry_date >= date('now') ORDER BY expiry_date LIMIT 10",
        engine,
    )
    if not upcoming_expiries.empty:
        upcoming_expiries["expiry_date"] = pd.to_datetime(upcoming_expiries["expiry_date"])

    iso_by_standard = pd.read_sql(
        "SELECT iso_standard, COUNT(*) AS count FROM iso_projects GROUP BY iso_standard",
        engine,
    )

    return {
        "audits_by_month": audits_by_month,
        "audits_by_status": audits_by_status,
        "top_cities": top_cities,
        "upcoming_expiries": upcoming_expiries,
        "iso_by_standard": iso_by_standard,
    }
