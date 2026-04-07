

import os
import pandas as pd
import psycopg2

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "equipment_monitoring"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}


def get_connection():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )


def load_dashboard_data():
    conn = get_connection()

    latest_per_machine_query = """
    SELECT DISTINCT ON (equipment_id)
        id,
        frame_id,
        equipment_id,
        equipment_class,
        timestamp_str,
        current_state,
        current_activity,
        motion_source,
        total_tracked_seconds,
        total_active_seconds,
        total_idle_seconds,
        utilization_percent
    FROM equipment_events
    ORDER BY equipment_id, id DESC;
    """

    recent_events_query = """
    SELECT
        id,
        frame_id,
        equipment_id,
        equipment_class,
        timestamp_str,
        current_state,
        current_activity,
        motion_source,
        total_tracked_seconds,
        total_active_seconds,
        total_idle_seconds,
        utilization_percent
    FROM equipment_events
    ORDER BY id DESC
    LIMIT 40;
    """

    trend_query = """
    SELECT
        id,
        frame_id,
        equipment_id,
        timestamp_str,
        utilization_percent,
        total_active_seconds,
        total_idle_seconds,
        current_activity,
        current_state
    FROM equipment_events
    ORDER BY id ASC;
    """

    activity_dist_query = """
    SELECT
        current_activity,
        COUNT(*) AS count
    FROM equipment_events
    GROUP BY current_activity
    ORDER BY count DESC;
    """

    latest_df = pd.read_sql(latest_per_machine_query, conn)
    recent_df = pd.read_sql(recent_events_query, conn)
    trend_df = pd.read_sql(trend_query, conn)
    activity_df = pd.read_sql(activity_dist_query, conn)

    conn.close()
    return latest_df, recent_df, trend_df, activity_df