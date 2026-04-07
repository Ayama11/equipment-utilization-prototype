import csv
import json
import os
from collections import defaultdict

input_csv = "outputs/tracked_activity_timeline.csv"
events_output_csv = "outputs/tracked_equipment_events.csv"
payloads_output_jsonl = "outputs/kafka_payloads.jsonl"

# إذا عندك أكثر من نوع معدة لاحقًا يمكن تغييره
default_equipment_class = "excavator"


def load_rows(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "frame_idx": int(row["frame_idx"]),
                "track_id": int(row["track_id"]),
                "timestamp_sec": float(row["timestamp_sec"]),
                "motion_source": row["motion_source"],
                "state": row["state"],
                "activity": row["activity"],
                "phase": row.get("phase", "RUNNING")
            })
    return rows


def split_by_track(rows):
    rows_by_track = defaultdict(list)
    for row in rows:
        rows_by_track[row["track_id"]].append(row)

    for track_id in rows_by_track:
        rows_by_track[track_id].sort(key=lambda r: r["frame_idx"])

    return rows_by_track


def estimate_frame_dt(rows):
    if len(rows) < 2:
        return 1.0 / 30.0

    diffs = []
    for i in range(1, len(rows)):
        dt = rows[i]["timestamp_sec"] - rows[i - 1]["timestamp_sec"]
        if dt > 0:
            diffs.append(dt)

    return min(diffs) if diffs else 1.0 / 30.0


def sec_to_timestamp_str(seconds_value):
    total_ms = int(round(seconds_value * 1000.0))
    hours = total_ms // 3600000
    total_ms %= 3600000
    minutes = total_ms // 60000
    total_ms %= 60000
    seconds = total_ms // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def canonical_equipment_id(track_id):
    return f"EX-{track_id:03d}"


def build_events_and_payloads(rows_by_track):
    csv_rows = []
    payloads = []

    for track_id, track_rows in rows_by_track.items():
        equipment_id = canonical_equipment_id(track_id)
        equipment_class = default_equipment_class
        frame_dt = estimate_frame_dt(track_rows)

        total_tracked = 0.0
        total_active = 0.0
        total_idle = 0.0

        for i, row in enumerate(track_rows):
            # نحسب الزمن التراكمي بطريقة online تقريبية
            if i == 0:
                delta_t = frame_dt
            else:
                delta_t = row["timestamp_sec"] - track_rows[i - 1]["timestamp_sec"]
                if delta_t <= 0:
                    delta_t = frame_dt

            total_tracked += delta_t

            if row["state"] == "ACTIVE":
                total_active += delta_t
            else:
                total_idle += delta_t

            utilization_percent = (total_active / total_tracked * 100.0) if total_tracked > 0 else 0.0

            timestamp_str = sec_to_timestamp_str(row["timestamp_sec"])

            csv_rows.append({
                "frame_id": row["frame_idx"],
                "equipment_id": equipment_id,
                "equipment_class": equipment_class,
                "timestamp_sec": round(row["timestamp_sec"], 2),
                "timestamp_str": timestamp_str,
                "current_state": row["state"],
                "current_activity": row["activity"],
                "motion_source": row["motion_source"],
                "phase": row["phase"],
                "total_tracked_seconds": round(total_tracked, 2),
                "total_active_seconds": round(total_active, 2),
                "total_idle_seconds": round(total_idle, 2),
                "utilization_percent": round(utilization_percent, 2)
            })

            payload = {
                "frame_id": row["frame_idx"],
                "equipment_id": equipment_id,
                "equipment_class": equipment_class,
                "timestamp": timestamp_str,
                "utilization": {
                    "current_state": row["state"],
                    "current_activity": row["activity"],
                    "motion_source": row["motion_source"]
                },
                "time_analytics": {
                    "total_tracked_seconds": round(total_tracked, 2),
                    "total_active_seconds": round(total_active, 2),
                    "total_idle_seconds": round(total_idle, 2),
                    "utilization_percent": round(utilization_percent, 2)
                }
            }

            payloads.append(payload)

    csv_rows.sort(key=lambda r: (r["equipment_id"], r["frame_id"]))
    payloads.sort(key=lambda p: (p["equipment_id"], p["frame_id"]))

    return csv_rows, payloads


def save_events_csv(csv_path, rows):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "frame_id",
            "equipment_id",
            "equipment_class",
            "timestamp_sec",
            "timestamp_str",
            "current_state",
            "current_activity",
            "motion_source",
            "phase",
            "total_tracked_seconds",
            "total_active_seconds",
            "total_idle_seconds",
            "utilization_percent"
        ])

        for row in rows:
            writer.writerow([
                row["frame_id"],
                row["equipment_id"],
                row["equipment_class"],
                row["timestamp_sec"],
                row["timestamp_str"],
                row["current_state"],
                row["current_activity"],
                row["motion_source"],
                row["phase"],
                row["total_tracked_seconds"],
                row["total_active_seconds"],
                row["total_idle_seconds"],
                row["utilization_percent"]
            ])


def save_payloads_jsonl(jsonl_path, payloads):
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for payload in payloads:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def print_summary(csv_rows, payloads):
    if not csv_rows:
        print("No event rows generated.")
        return

    by_equipment = defaultdict(list)
    for row in csv_rows:
        by_equipment[row["equipment_id"]].append(row)

    print(f"Generated event rows: {len(csv_rows)}")
    print(f"Generated Kafka payloads: {len(payloads)}")

    for equipment_id, rows in by_equipment.items():
        last_row = rows[-1]
        print(
            f"{equipment_id} | "
            f"tracked={last_row['total_tracked_seconds']}s | "
            f"active={last_row['total_active_seconds']}s | "
            f"idle={last_row['total_idle_seconds']}s | "
            f"utilization={last_row['utilization_percent']}%"
        )


def main():
    rows = load_rows(input_csv)
    rows_by_track = split_by_track(rows)

    csv_rows, payloads = build_events_and_payloads(rows_by_track)

    os.makedirs("outputs", exist_ok=True)
    save_events_csv(events_output_csv, csv_rows)
    save_payloads_jsonl(payloads_output_jsonl, payloads)

    print(f"Saved tracked equipment events to: {events_output_csv}")
    print(f"Saved Kafka payloads to: {payloads_output_jsonl}")
    print_summary(csv_rows, payloads)


if __name__ == "__main__":
    main()