import csv
import math
import os

input_csv = "data/excavator_boxes.csv"
output_csv = "outputs/tracked_excavator_boxes.csv"

# إعدادات tracking
max_missing_frames = 10
min_iou_match = 0.15
max_center_distance = 120.0
max_size_ratio_diff = 0.60


def compute_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a["x1"], box_a["y1"], box_a["x2"], box_a["y2"]
    bx1, by1, bx2, by2 = box_b["x1"], box_b["y1"], box_b["x2"], box_b["y2"]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

    union_area = area_a + area_b - inter_area
    if union_area <= 0:
        return 0.0

    return inter_area / union_area


def center_and_size(box):
    x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w / 2.0
    cy = y1 + h / 2.0
    return cx, cy, w, h


def center_distance(box_a, box_b):
    cax, cay, _, _ = center_and_size(box_a)
    cbx, cby, _, _ = center_and_size(box_b)
    return math.hypot(cax - cbx, cay - cby)


def size_ratio_difference(box_a, box_b):
    _, _, wa, ha = center_and_size(box_a)
    _, _, wb, hb = center_and_size(box_b)

    if wa <= 0 or ha <= 0 or wb <= 0 or hb <= 0:
        return 1.0

    area_a = wa * ha
    area_b = wb * hb
    larger = max(area_a, area_b)
    smaller = min(area_a, area_b)

    if larger <= 0:
        return 1.0

    return 1.0 - (smaller / larger)


def detection_to_box(row):
    x1 = int(float(row["x1"]))
    y1 = int(float(row["y1"]))
    x2 = int(float(row["x2"]))
    y2 = int(float(row["y2"]))

    cx, cy, w, h = center_and_size({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    return {
        "frame_idx": int(row["frame_idx"]),
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "confidence": float(row["confidence"]) if row.get("confidence", "") != "" else None,
        "cx": round(cx, 2),
        "cy": round(cy, 2),
        "w": round(w, 2),
        "h": round(h, 2),
    }


def load_detections_grouped(csv_path):
    frames = {}
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["x1"] == "":
                continue

            det = detection_to_box(row)
            frame_idx = det["frame_idx"]

            if frame_idx not in frames:
                frames[frame_idx] = []
            frames[frame_idx].append(det)

    return frames


def match_detection_to_track(det, active_tracks):
    best_track_id = None
    best_score = -1.0

    for track_id, track in active_tracks.items():
        last_box = track["last_box"]
        missing_count = track["missing_count"]

        # إذا track مختفية كثير، لا نحاول ربطها
        if missing_count > max_missing_frames:
            continue

        iou = compute_iou(det, last_box)
        dist = center_distance(det, last_box)
        size_diff = size_ratio_difference(det, last_box)

        # شرط أولي للقبول
        if iou < min_iou_match and dist > max_center_distance:
            continue

        if size_diff > max_size_ratio_diff:
            continue

        # score بسيط يوازن بين iou والقرب
        distance_score = max(0.0, 1.0 - (dist / max_center_distance))
        size_score = max(0.0, 1.0 - size_diff)

        score = (0.50 * iou) + (0.30 * distance_score) + (0.20 * size_score)

        if score > best_score:
            best_score = score
            best_track_id = track_id

    return best_track_id, best_score


def main():
    detections_by_frame = load_detections_grouped(input_csv)

    if not detections_by_frame:
        print("No detections found.")
        return

    all_frames = sorted(detections_by_frame.keys())

    next_track_id = 1
    active_tracks = {}
    output_rows = []

    for frame_idx in all_frames:
        detections = detections_by_frame[frame_idx]

        matched_track_ids = set()
        used_detection_indices = set()

        # 1) حاول ربط كل detection مع track موجودة
        for det_idx, det in enumerate(detections):
            track_id, score = match_detection_to_track(det, active_tracks)

            if track_id is not None and track_id not in matched_track_ids:
                active_tracks[track_id]["last_box"] = {
                    "x1": det["x1"],
                    "y1": det["y1"],
                    "x2": det["x2"],
                    "y2": det["y2"]
                }
                active_tracks[track_id]["last_frame"] = frame_idx
                active_tracks[track_id]["missing_count"] = 0

                matched_track_ids.add(track_id)
                used_detection_indices.add(det_idx)

                output_rows.append({
                    "frame_idx": frame_idx,
                    "track_id": track_id,
                    "x1": det["x1"],
                    "y1": det["y1"],
                    "x2": det["x2"],
                    "y2": det["y2"],
                    "cx": det["cx"],
                    "cy": det["cy"],
                    "w": det["w"],
                    "h": det["h"],
                    "confidence": det["confidence"],
                    "matched_existing_track": 1,
                    "missing_count": 0
                })

        # 2) أي detection لم تُربط، افتح لها track جديدة
        for det_idx, det in enumerate(detections):
            if det_idx in used_detection_indices:
                continue

            track_id = next_track_id
            next_track_id += 1

            active_tracks[track_id] = {
                "last_box": {
                    "x1": det["x1"],
                    "y1": det["y1"],
                    "x2": det["x2"],
                    "y2": det["y2"]
                },
                "last_frame": frame_idx,
                "missing_count": 0
            }

            matched_track_ids.add(track_id)

            output_rows.append({
                "frame_idx": frame_idx,
                "track_id": track_id,
                "x1": det["x1"],
                "y1": det["y1"],
                "x2": det["x2"],
                "y2": det["y2"],
                "cx": det["cx"],
                "cy": det["cy"],
                "w": det["w"],
                "h": det["h"],
                "confidence": det["confidence"],
                "matched_existing_track": 0,
                "missing_count": 0
            })

        # 3) زيد missing_count لأي track لم تُشاهد في هذا frame
        for track_id in list(active_tracks.keys()):
            if track_id not in matched_track_ids:
                active_tracks[track_id]["missing_count"] += 1

        # 4) احذف الـ tracks المنتهية جدًا
        for track_id in list(active_tracks.keys()):
            if active_tracks[track_id]["missing_count"] > max_missing_frames:
                del active_tracks[track_id]

    os.makedirs("outputs", exist_ok=True)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "frame_idx",
            "track_id",
            "x1",
            "y1",
            "x2",
            "y2",
            "cx",
            "cy",
            "w",
            "h",
            "confidence",
            "matched_existing_track",
            "missing_count"
        ])
        for row in output_rows:
            writer.writerow([
                row["frame_idx"],
                row["track_id"],
                row["x1"],
                row["y1"],
                row["x2"],
                row["y2"],
                row["cx"],
                row["cy"],
                row["w"],
                row["h"],
                row["confidence"],
                row["matched_existing_track"],
                row["missing_count"]
            ])

    unique_tracks = sorted(set(r["track_id"] for r in output_rows))
    print(f"Saved tracked boxes to: {output_csv}")
    print(f"Rows saved: {len(output_rows)}")
    print(f"Unique track IDs: {unique_tracks}")


if __name__ == "__main__":
    main()