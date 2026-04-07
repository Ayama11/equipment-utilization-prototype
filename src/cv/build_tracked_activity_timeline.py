import cv2
import csv
import os
from collections import Counter, deque
from statistics import mean

video_path = "data/clips/test_clip.mp4"
tracked_boxes_csv = "outputs/tracked_excavator_boxes.csv"
output_csv = "outputs/tracked_activity_timeline.csv"

# ---------------------------------
# General settings
# ---------------------------------
zone_size = (64, 64)
motion_window = 7
bootstrap_frames = 10

# ---------------------------------
# General thresholds
# هادول أعمّ من النهج القديم
# ---------------------------------
active_enter_arm = 0.75
active_enter_body = 0.55

inactive_exit_arm = 0.28
inactive_exit_body = 0.22

arm_only_arm_min = 0.55
arm_only_body_max = 0.24

min_active_frames = 4
min_inactive_frames = 8

min_active_run_sec = 0.25
min_inactive_run_sec = 0.40
min_activity_run_sec = 0.30

flow_mag_threshold = 0.35

# activity hints
dig_hint_min = 0.40
dump_hint_min = 0.80
dump_after_active_frames = 8


def preprocess_gray(gray):
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    return gray


def resize_gray(img_bgr, target_size):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, target_size, interpolation=cv2.INTER_AREA)
    resized = preprocess_gray(resized)
    return resized


def flow_motion_score(prev_gray, curr_gray, mag_threshold=0.35):
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray,
        curr_gray,
        None,
        0.5,
        3,
        15,
        3,
        5,
        1.2,
        0
    )

    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    moving_mask = mag > mag_threshold
    moving_ratio = float(moving_mask.mean())
    mean_mag = float(mag.mean())
    strong_mag = float(mag[moving_mask].mean()) if moving_mask.any() else 0.0

    score = (0.55 * mean_mag) + (0.45 * strong_mag * moving_ratio)
    return score, mean_mag, moving_ratio


def load_tracked_boxes(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "frame_idx": int(row["frame_idx"]),
                "track_id": int(row["track_id"]),
                "x1": int(float(row["x1"])),
                "y1": int(float(row["y1"])),
                "x2": int(float(row["x2"])),
                "y2": int(float(row["y2"]))
            })
    rows.sort(key=lambda r: (r["track_id"], r["frame_idx"]))
    return rows


def mean_of_queue(q):
    return sum(q) / len(q) if q else 0.0


def build_segments(rows, key_name):
    segments = []
    if not rows:
        return segments

    start_idx = 0
    current_value = rows[0][key_name]

    for i in range(1, len(rows)):
        if rows[i][key_name] != current_value:
            segments.append((start_idx, i - 1, current_value))
            start_idx = i
            current_value = rows[i][key_name]

    segments.append((start_idx, len(rows) - 1, current_value))
    return segments


def segment_duration_sec(rows, start_i, end_i, frame_dt):
    return (rows[end_i]["timestamp_sec"] - rows[start_i]["timestamp_sec"]) + frame_dt


def segment_contains_bootstrap(rows, start_i, end_i):
    for j in range(start_i, end_i + 1):
        if rows[j]["phase"] == "BOOTSTRAP":
            return True
    return False


def cleanup_short_state_runs(rows, fps):
    if not rows:
        return rows

    frame_dt = 1.0 / fps
    segments = build_segments(rows, "state")

    for seg_idx, (start_i, end_i, state) in enumerate(segments):
        if segment_contains_bootstrap(rows, start_i, end_i):
            continue

        duration = segment_duration_sec(rows, start_i, end_i, frame_dt)
        min_required = min_inactive_run_sec if state == "INACTIVE" else min_active_run_sec

        if duration >= min_required:
            continue

        prev_state = segments[seg_idx - 1][2] if seg_idx > 0 else None
        next_state = segments[seg_idx + 1][2] if seg_idx < len(segments) - 1 else None

        replacement = None
        if prev_state == next_state and prev_state is not None:
            replacement = prev_state
        elif prev_state is not None:
            replacement = prev_state
        elif next_state is not None:
            replacement = next_state

        if replacement is not None:
            for j in range(start_i, end_i + 1):
                if rows[j]["phase"] == "BOOTSTRAP":
                    continue
                rows[j]["state"] = replacement
                if replacement == "INACTIVE":
                    rows[j]["activity"] = "WAITING"

    return rows


def cleanup_short_activity_runs(rows, fps):
    if not rows:
        return rows

    frame_dt = 1.0 / fps
    segments = build_segments(rows, "activity")

    for seg_idx, (start_i, end_i, activity) in enumerate(segments):
        if segment_contains_bootstrap(rows, start_i, end_i):
            continue

        duration = segment_duration_sec(rows, start_i, end_i, frame_dt)
        if duration >= min_activity_run_sec:
            continue

        if rows[start_i]["state"] == "INACTIVE":
            for j in range(start_i, end_i + 1):
                if rows[j]["phase"] == "BOOTSTRAP":
                    continue
                rows[j]["activity"] = "WAITING"
            continue

        prev_activity = segments[seg_idx - 1][2] if seg_idx > 0 else None
        next_activity = segments[seg_idx + 1][2] if seg_idx < len(segments) - 1 else None

        replacement = None
        if prev_activity == next_activity and prev_activity is not None:
            replacement = prev_activity
        elif prev_activity is not None:
            replacement = prev_activity
        elif next_activity is not None:
            replacement = next_activity

        if replacement is not None:
            for j in range(start_i, end_i + 1):
                if rows[j]["phase"] == "BOOTSTRAP":
                    continue
                if rows[j]["state"] == "ACTIVE":
                    rows[j]["activity"] = replacement

    return rows


def recompute_motion_source_and_waiting(rows):
    for row in rows:
        if row["phase"] == "BOOTSTRAP":
            row["state"] = "INACTIVE"
            row["activity"] = "WAITING"
            row["motion_source"] = "no_significant_motion"
            continue

        if row["state"] == "INACTIVE":
            row["activity"] = "WAITING"
            row["motion_source"] = "no_significant_motion"
        else:
            if (
                row["arm_motion_smooth"] >= arm_only_arm_min and
                row["body_motion_smooth"] < arm_only_body_max
            ):
                row["motion_source"] = "arm_only"
            else:
                row["motion_source"] = "full_machine"

            if row["activity"] == "WAITING":
                row["activity"] = "SWINGING_LOADING"
    return rows


def print_motion_stats(rows):
    if not rows:
        print("No rows available for diagnostics.")
        return

    body_values = [r["body_motion_smooth"] for r in rows]
    arm_values = [r["arm_motion_smooth"] for r in rows]
    dig_hint_values = [r["dig_hint_motion_smooth"] for r in rows]
    dump_hint_values = [r["dump_hint_motion_smooth"] for r in rows]

    phase_counts = Counter(r["phase"] for r in rows)
    state_counts = Counter(r["state"] for r in rows)
    activity_counts = Counter(r["activity"] for r in rows)
    motion_source_counts = Counter(r["motion_source"] for r in rows)

    print("\n=== Diagnostics ===")
    print("Phase counts:")
    print(phase_counts)
    print("\nState counts:")
    print(state_counts)
    print("\nActivity counts:")
    print(activity_counts)
    print("\nMotion source counts:")
    print(motion_source_counts)

    print("\nSmoothed motion stats:")
    print(f"body_motion_smooth      -> min={min(body_values):.3f}, mean={mean(body_values):.3f}, max={max(body_values):.3f}")
    print(f"arm_motion_smooth       -> min={min(arm_values):.3f}, mean={mean(arm_values):.3f}, max={max(arm_values):.3f}")
    print(f"dig_hint_motion_smooth  -> min={min(dig_hint_values):.3f}, mean={mean(dig_hint_values):.3f}, max={max(dig_hint_values):.3f}")
    print(f"dump_hint_motion_smooth -> min={min(dump_hint_values):.3f}, mean={mean(dump_hint_values):.3f}, max={max(dump_hint_values):.3f}")


tracked_rows = load_tracked_boxes(tracked_boxes_csv)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: could not open video.")
    raise SystemExit(1)

fps = cap.get(cv2.CAP_PROP_FPS)

tracked_by_frame = {}
for row in tracked_rows:
    tracked_by_frame.setdefault(row["frame_idx"], []).append(row)

prev_zones_by_track = {}
track_memory = {}
output_rows = []

frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_idx not in tracked_by_frame:
        frame_idx += 1
        continue

    detections = tracked_by_frame[frame_idx]

    for det in detections:
        track_id = det["track_id"]
        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            continue

        h, w = roi.shape[:2]
        if h < 10 or w < 10:
            continue

        # ---------------------------------
        # New general zones
        # ---------------------------------
        # body zone: جسم المعدة/القاعدة
        body_x1 = int(w * 0.26)
        body_x2 = int(w * 0.74)
        body_y1 = int(h * 0.68)
        body_y2 = int(h * 0.95)

        # arm zone: الجزء العلوي/الذراع بشكل عام
        arm_x1 = int(w * 0.05)
        arm_x2 = int(w * 0.92)
        arm_y1 = int(h * 0.12)
        arm_y2 = int(h * 0.72)

        # dig hint: أسفل/يسار
        dig_x1 = 0
        dig_x2 = int(w * 0.55)
        dig_y1 = int(h * 0.50)
        dig_y2 = h

        # dump hint: أعلى/يمين
        dump_x1 = int(w * 0.72)
        dump_x2 = w
        dump_y1 = 0
        dump_y2 = int(h * 0.24)

        body_roi = roi[body_y1:body_y2, body_x1:body_x2]
        arm_roi = roi[arm_y1:arm_y2, arm_x1:arm_x2]
        dig_roi = roi[dig_y1:dig_y2, dig_x1:dig_x2]
        dump_roi = roi[dump_y1:dump_y2, dump_x1:dump_x2]

        if (
            body_roi.size == 0 or
            arm_roi.size == 0 or
            dig_roi.size == 0 or
            dump_roi.size == 0
        ):
            continue

        body_gray = resize_gray(body_roi, zone_size)
        arm_gray = resize_gray(arm_roi, zone_size)
        dig_gray = resize_gray(dig_roi, zone_size)
        dump_gray = resize_gray(dump_roi, zone_size)

        if track_id not in prev_zones_by_track:
            prev_zones_by_track[track_id] = {
                "body": body_gray,
                "arm": arm_gray,
                "dig": dig_gray,
                "dump": dump_gray
            }

            track_memory[track_id] = {
                "body_q": deque(maxlen=motion_window),
                "arm_q": deque(maxlen=motion_window),
                "dig_q": deque(maxlen=motion_window),
                "dump_q": deque(maxlen=motion_window),
                "state": None,
                "candidate_state": None,
                "candidate_count": 0,
                "activity_q": deque(maxlen=motion_window),
                "phase": "BOOTSTRAP",
                "seen_frames": 0,
                "active_frames_since_bootstrap": 0
            }
            continue

        prev_body_gray = prev_zones_by_track[track_id]["body"]
        prev_arm_gray = prev_zones_by_track[track_id]["arm"]
        prev_dig_gray = prev_zones_by_track[track_id]["dig"]
        prev_dump_gray = prev_zones_by_track[track_id]["dump"]

        body_motion, _, body_move_ratio = flow_motion_score(prev_body_gray, body_gray, flow_mag_threshold)
        arm_motion, _, arm_move_ratio = flow_motion_score(prev_arm_gray, arm_gray, flow_mag_threshold)
        dig_hint_motion, _, dig_move_ratio = flow_motion_score(prev_dig_gray, dig_gray, flow_mag_threshold)
        dump_hint_motion, _, dump_move_ratio = flow_motion_score(prev_dump_gray, dump_gray, flow_mag_threshold)

        mem = track_memory[track_id]
        mem["seen_frames"] += 1

        mem["body_q"].append(body_motion)
        mem["arm_q"].append(arm_motion)
        mem["dig_q"].append(dig_hint_motion)
        mem["dump_q"].append(dump_hint_motion)

        body_s = mean_of_queue(mem["body_q"])
        arm_s = mean_of_queue(mem["arm_q"])
        dig_s = mean_of_queue(mem["dig_q"])
        dump_s = mean_of_queue(mem["dump_q"])

        # ---------------------------------
        # State machine
        # ---------------------------------
        if mem["phase"] == "BOOTSTRAP":
            if mem["seen_frames"] < bootstrap_frames:
                stable_state = "INACTIVE"
                raw_state = "INACTIVE"
            else:
                initial_state = "ACTIVE" if (arm_s >= active_enter_arm or body_s >= active_enter_body) else "INACTIVE"
                mem["state"] = initial_state
                mem["phase"] = "RUNNING"
                stable_state = mem["state"]
                raw_state = stable_state
        else:
            current_state = mem["state"]

            if current_state == "INACTIVE":
                raw_state = "ACTIVE" if (arm_s >= active_enter_arm or body_s >= active_enter_body) else "INACTIVE"
            else:
                raw_state = "INACTIVE" if (arm_s < inactive_exit_arm and body_s < inactive_exit_body) else "ACTIVE"

            if raw_state == current_state:
                mem["candidate_state"] = None
                mem["candidate_count"] = 0
            else:
                if mem["candidate_state"] != raw_state:
                    mem["candidate_state"] = raw_state
                    mem["candidate_count"] = 1
                else:
                    mem["candidate_count"] += 1

                required = min_active_frames if raw_state == "ACTIVE" else min_inactive_frames
                if mem["candidate_count"] >= required:
                    mem["state"] = raw_state
                    mem["candidate_state"] = None
                    mem["candidate_count"] = 0

            stable_state = mem["state"]

        # ---------------------------------
        # Activity logic (phase-based)
        # ---------------------------------
        if mem["phase"] == "BOOTSTRAP":
            activity = "WAITING"
            motion_source = "no_significant_motion"
            mem["activity_q"].clear()
        elif stable_state == "INACTIVE":
            activity = "WAITING"
            motion_source = "no_significant_motion"
            mem["activity_q"].clear()
            mem["active_frames_since_bootstrap"] = 0
        else:
            mem["active_frames_since_bootstrap"] += 1

            # motion source
            if arm_s >= arm_only_arm_min and body_s < arm_only_body_max:
                motion_source = "arm_only"
            else:
                motion_source = "full_machine"

            # activity by temporal hints
            if dig_s >= dig_hint_min and arm_s >= active_enter_arm:
                raw_activity = "DIGGING"
            elif (
                dump_s >= dump_hint_min and
                mem["active_frames_since_bootstrap"] >= dump_after_active_frames
            ):
                raw_activity = "DUMPING"
            else:
                raw_activity = "SWINGING_LOADING"

            mem["activity_q"].append(raw_activity)
            vote_counts = Counter(mem["activity_q"])
            activity = vote_counts.most_common(1)[0][0]

        timestamp = frame_idx / fps

        output_rows.append({
            "frame_idx": frame_idx,
            "track_id": track_id,
            "timestamp_sec": round(timestamp, 2),

            "body_motion": round(body_motion, 3),
            "arm_motion": round(arm_motion, 3),
            "dig_hint_motion": round(dig_hint_motion, 3),
            "dump_hint_motion": round(dump_hint_motion, 3),

            "body_move_ratio": round(body_move_ratio, 4),
            "arm_move_ratio": round(arm_move_ratio, 4),
            "dig_hint_move_ratio": round(dig_move_ratio, 4),
            "dump_hint_move_ratio": round(dump_move_ratio, 4),

            "body_motion_smooth": round(body_s, 3),
            "arm_motion_smooth": round(arm_s, 3),
            "dig_hint_motion_smooth": round(dig_s, 3),
            "dump_hint_motion_smooth": round(dump_s, 3),

            "motion_source": motion_source,
            "state": stable_state,
            "activity": activity,
            "phase": mem["phase"]
        })

        prev_zones_by_track[track_id] = {
            "body": body_gray,
            "arm": arm_gray,
            "dig": dig_gray,
            "dump": dump_gray
        }

    frame_idx += 1

cap.release()

# ---------------------------------
# Cleanup
# ---------------------------------
rows_by_track = {}
for row in output_rows:
    rows_by_track.setdefault(row["track_id"], []).append(row)

final_rows = []
for track_id, rows in rows_by_track.items():
    rows.sort(key=lambda r: r["frame_idx"])
    rows = cleanup_short_state_runs(rows, fps)
    rows = cleanup_short_activity_runs(rows, fps)
    rows = recompute_motion_source_and_waiting(rows)
    final_rows.extend(rows)

final_rows.sort(key=lambda r: (r["track_id"], r["frame_idx"]))

os.makedirs("outputs", exist_ok=True)

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "frame_idx",
        "track_id",
        "timestamp_sec",

        "body_motion",
        "arm_motion",
        "dig_hint_motion",
        "dump_hint_motion",

        "body_move_ratio",
        "arm_move_ratio",
        "dig_hint_move_ratio",
        "dump_hint_move_ratio",

        "body_motion_smooth",
        "arm_motion_smooth",
        "dig_hint_motion_smooth",
        "dump_hint_motion_smooth",

        "motion_source",
        "state",
        "activity",
        "phase"
    ])

    for row in final_rows:
        writer.writerow([
            row["frame_idx"],
            row["track_id"],
            row["timestamp_sec"],

            row["body_motion"],
            row["arm_motion"],
            row["dig_hint_motion"],
            row["dump_hint_motion"],

            row["body_move_ratio"],
            row["arm_move_ratio"],
            row["dig_hint_move_ratio"],
            row["dump_hint_move_ratio"],

            row["body_motion_smooth"],
            row["arm_motion_smooth"],
            row["dig_hint_motion_smooth"],
            row["dump_hint_motion_smooth"],

            row["motion_source"],
            row["state"],
            row["activity"],
            row["phase"]
        ])

print(f"Saved tracked activity timeline to: {output_csv}")
print(f"Rows saved: {len(final_rows)}")
if final_rows:
    print("First row:", final_rows[0])
    print("Last row:", final_rows[-1])

print_motion_stats(final_rows)