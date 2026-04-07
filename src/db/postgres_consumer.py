

import json
import os
import time
from kafka import KafkaConsumer
import psycopg2

TOPIC_NAME = os.getenv("KAFKA_TOPIC", "equipment.events")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "postgres-consumer-group")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "equipment_monitoring"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres")
}


def create_db_connection(retries=20, delay=3):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                dbname=DB_CONFIG["dbname"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"]
            )
            return conn
        except Exception as e:
            last_error = e
            print(f"[DB] Connection failed (attempt {attempt}/{retries}): {e}")
            time.sleep(delay)

    raise last_error


def create_table_if_not_exists(conn):
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS equipment_events (
        id SERIAL PRIMARY KEY,
        frame_id INTEGER,
        equipment_id TEXT,
        equipment_class TEXT,
        timestamp_str TEXT,
        current_state TEXT,
        current_activity TEXT,
        motion_source TEXT,
        total_tracked_seconds DOUBLE PRECISION,
        total_active_seconds DOUBLE PRECISION,
        total_idle_seconds DOUBLE PRECISION,
        utilization_percent DOUBLE PRECISION
    );
    """

    with conn.cursor() as cur:
        cur.execute(create_table_sql)
    conn.commit()


def insert_event(conn, payload):
    insert_sql = """
    INSERT INTO equipment_events (
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
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    values = (
        payload["frame_id"],
        payload["equipment_id"],
        payload["equipment_class"],
        payload["timestamp"],
        payload["utilization"]["current_state"],
        payload["utilization"]["current_activity"],
        payload["utilization"]["motion_source"],
        payload["time_analytics"]["total_tracked_seconds"],
        payload["time_analytics"]["total_active_seconds"],
        payload["time_analytics"]["total_idle_seconds"],
        payload["time_analytics"]["utilization_percent"]
    )

    with conn.cursor() as cur:
        cur.execute(insert_sql, values)
    conn.commit()


def create_consumer():
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=GROUP_ID,
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )


def main():
    conn = create_db_connection()
    create_table_if_not_exists(conn)

    consumer = create_consumer()

    print("Listening to Kafka and saving events to PostgreSQL...\n")

    for message in consumer:
        payload = message.value
        insert_event(conn, payload)

        print(
            f"Saved to DB | frame_id={payload['frame_id']} | "
            f"equipment={payload['equipment_id']} | "
            f"state={payload['utilization']['current_state']} | "
            f"activity={payload['utilization']['current_activity']}"
        )


if __name__ == "__main__":
    main()