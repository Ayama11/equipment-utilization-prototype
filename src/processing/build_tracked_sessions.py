
import csv
import os

input_csv = "outputs/tracked_activity_timeline.csv"
idle_output_csv = "outputs/tracked_idle_sessions.csv"
activity_output_csv = "outputs/tracked_activity_sessions.csv"

min_idle_duration_sec = 0.3
min_activity_duration_sec = 0.3


def load_rows(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "frame_idx": int(row["frame_idx"]),
                "track_id": int(row["track_id"]),
                "timestamp_sec": float(row["timestamp_sec"]),
                "state": row["state"],
                "activity": row["activity"]
            })
    return rows


def split_by_track(rows):
    rows_by_track = {}
    for row in rows:
        rows_by_track.setdefault(row["track_id"], []).append(row)

    for tid in rows_by_track:
        rows_by_track[tid].sort(key=lambda r: r["frame_idx"])

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


def extract_state_sessions(rows, target_state, frame_dt):
    sessions = []
    if not rows:
        return sessions

    start_idx = None

    for i, row in enumerate(rows):
        if row["state"] == target_state and start_idx is None:
            start_idx = i
        elif row["state"] != target_state and start_idx is not None:
            start_row = rows[start_idx]
            end_row = rows[i - 1]
            duration = (end_row["timestamp_sec"] - start_row["timestamp_sec"]) + frame_dt

            sessions.append({
                "track_id": start_row["track_id"],
                "state": target_state,
                "start_frame": start_row["frame_idx"],
                "end_frame": end_row["frame_idx"],
                "start_sec": round(start_row["timestamp_sec"], 2),
                "end_sec": round(end_row["timestamp_sec"] + frame_dt, 2),
                "duration_sec": round(duration, 2)
            })
            start_idx = None

    if start_idx is not None:
        start_row = rows[start_idx]
        end_row = rows[-1]
        duration = (end_row["timestamp_sec"] - start_row["timestamp_sec"]) + frame_dt

        sessions.append({
            "track_id": start_row["track_id"],
            "state": target_state,
            "start_frame": start_row["frame_idx"],
            "end_frame": end_row["frame_idx"],
            "start_sec": round(start_row["timestamp_sec"], 2),
            "end_sec": round(end_row["timestamp_sec"] + frame_dt, 2),
            "duration_sec": round(duration, 2)
        })

    return sessions


def extract_activity_sessions(rows, frame_dt):
    sessions = []
    if not rows:
        return sessions

    start_idx = 0
    current_activity = rows[0]["activity"]

    for i in range(1, len(rows)):
        if rows[i]["activity"] != current_activity:
            start_row = rows[start_idx]
            end_row = rows[i - 1]
            duration = (end_row["timestamp_sec"] - start_row["timestamp_sec"]) + frame_dt

            sessions.append({
                "track_id": start_row["track_id"],
                "activity": current_activity,
                "start_frame": start_row["frame_idx"],
                "end_frame": end_row["frame_idx"],
                "start_sec": round(start_row["timestamp_sec"], 2),
                "end_sec": round(end_row["timestamp_sec"] + frame_dt, 2),
                "duration_sec": round(duration, 2)
            })

            start_idx = i
            current_activity = rows[i]["activity"]

    start_row = rows[start_idx]
    end_row = rows[-1]
    duration = (end_row["timestamp_sec"] - start_row["timestamp_sec"]) + frame_dt

    sessions.append({
        "track_id": start_row["track_id"],
        "activity": current_activity,
        "start_frame": start_row["frame_idx"],
        "end_frame": end_row["frame_idx"],
        "start_sec": round(start_row["timestamp_sec"], 2),
        "end_sec": round(end_row["timestamp_sec"] + frame_dt, 2),
        "duration_sec": round(duration, 2)
    })

    return sessions


def save_idle_sessions(csv_path, sessions):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "track_id",
            "state",
            "start_frame",
            "end_frame",
            "start_sec",
            "end_sec",
            "duration_sec"
        ])
        for s in sessions:
            writer.writerow([
                s["track_id"],
                s["state"],
                s["start_frame"],
                s["end_frame"],
                s["start_sec"],
                s["end_sec"],
                s["duration_sec"]
            ])


def save_activity_sessions(csv_path, sessions):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "track_id",
            "activity",
            "start_frame",
            "end_frame",
            "start_sec",
            "end_sec",
            "duration_sec"
        ])
        for s in sessions:
            writer.writerow([
                s["track_id"],
                s["activity"],
                s["start_frame"],
                s["end_frame"],
                s["start_sec"],
                s["end_sec"],
                s["duration_sec"]
            ])


def main():
    rows = load_rows(input_csv)
    rows_by_track = split_by_track(rows)

    all_idle_sessions = []
    all_activity_sessions = []

    for track_id, track_rows in rows_by_track.items():
        frame_dt = estimate_frame_dt(track_rows)

        idle_sessions = extract_state_sessions(track_rows, "INACTIVE", frame_dt)
        idle_sessions = [s for s in idle_sessions if s["duration_sec"] >= min_idle_duration_sec]
        all_idle_sessions.extend(idle_sessions)

        activity_sessions = extract_activity_sessions(track_rows, frame_dt)
        activity_sessions = [s for s in activity_sessions if s["duration_sec"] >= min_activity_duration_sec]
        all_activity_sessions.extend(activity_sessions)

    os.makedirs("outputs", exist_ok=True)

    save_idle_sessions(idle_output_csv, all_idle_sessions)
    save_activity_sessions(activity_output_csv, all_activity_sessions)

    total_idle_from_sessions = round(sum(s["duration_sec"] for s in all_idle_sessions), 2)

    print(f"Saved tracked idle sessions to: {idle_output_csv}")
    print(f"Idle sessions count: {len(all_idle_sessions)}")
    print(f"Total idle time from sessions: {total_idle_from_sessions}s")
    if all_idle_sessions:
        print("Last idle session:", all_idle_sessions[-1])

    print(f"\nSaved tracked activity sessions to: {activity_output_csv}")
    print(f"Activity sessions count: {len(all_activity_sessions)}")
    if all_activity_sessions:
        print("Last activity session:", all_activity_sessions[-1])


if __name__ == "__main__":
    main()