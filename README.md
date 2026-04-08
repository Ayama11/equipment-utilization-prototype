# 🚜 Equipment Utilization & Activity Classification Prototype

A compact end-to-end prototype for excavator monitoring from video using **Computer Vision**, **Kafka**, **PostgreSQL**, and **Streamlit**.

This project demonstrates how to detect equipment in video, track it across frames, estimate utilization state (`ACTIVE` / `INACTIVE`), classify work activity (`DIGGING`, `SWINGING_LOADING`, `DUMPING`, `WAITING`), stream structured events through Kafka, store analytics in PostgreSQL, and visualize the results in an interactive dashboard.

---

## ✨ Overview

The goal of this project is to build a practical prototype for monitoring construction equipment from video.

The system combines:
- object detection,
- tracking,
- motion analysis,
- activity classification,
- event streaming,
- database storage,
- dashboard visualization.

The final analytics include:
- current machine state,
- current activity,
- total active time,
- total idle time,
- utilization percentage.

---

## 🧠 Detection Model

The object detector was trained separately using **YOLOv8n**.

### Training Data
The training set was built from:
- a dataset collected from **Roboflow**,
- plus additional images extracted from our own project videos.

This improved the detector’s fit to the actual excavator scene used in the final prototype.

### Training Workflow
The training process was implemented in a separate notebook, and the resulting weights and outputs were saved to Google Drive.

🔗 **Training notebook:**  
`<(https://colab.research.google.com/drive/1CDbFVZoZUHxPh97gNYzyS_HaOpCfRrly)>`

### Important Note
This repository focuses on the **post-detection pipeline**. It starts from available detection results (bounding-box data), then performs:
- tracking,
- utilization analysis,
- activity classification,
- Kafka payload generation,
- PostgreSQL storage,
- dashboard visualization.

---

## 🏗️ System Architecture

```text
Video Clip + Detection Boxes
        ↓
Tracking
        ↓
Motion / Activity Analysis
        ↓
Structured Events (JSON)
        ↓
Kafka
        ↓
PostgreSQL Consumer
        ↓
PostgreSQL
        ↓
Streamlit Dashboard

```

## ⚙️ Core Pipeline
1) Tracking

The system links detections across frames and assigns a persistent track_id to the excavator.

File:
src/tracking/build_tracks.py

Matching is based on:

*IoU
*center distance
*size consistency

2) Utilization Analysis

The tracked machine is analyzed to determine whether it is:

ACTIVE
INACTIVE

File:
src/cv/build_tracked_activity_timeline.py

This stage uses:

optical flow,
region-based motion analysis,
smoothing,
hysteresis,
cleanup of short noisy runs.

3) Articulated Motion Handling

A major challenge in excavator monitoring is that the arm may be moving while the lower body remains almost stationary.

To handle this, the machine ROI is divided into motion-sensitive regions such as:

body / base region
arm region
digging hint region
dumping hint region

This allows the system to distinguish:

arm_only
full_machine
no_significant_motion

As a result, the excavator is not incorrectly marked as idle when only the arm is active.

4) Activity Classification

The system classifies the current activity into:

DIGGING
SWINGING_LOADING
DUMPING
WAITING

The classification is heuristic-based and depends on:

motion intensity,
motion distribution across selected regions,
smoothing,
rule-based cleanup.
5) Time Analytics

The system computes:

total tracked time,
total active time,
total idle time,
utilization percentage.

File:
src/cv/tracked_equipment_events.py

6) Session Extraction

The repository also includes extraction of:

idle sessions,
activity sessions.

File:
src/processing/build_tracked_sessions.py

##📡 Event Streaming and Storage

Kafka

Structured JSON events are generated and sent through Kafka.

Relevant files:

src/cv/tracked_equipment_events.py
src/streaming/kafka_producer.py
src/streaming/kafka_consumer.py
PostgreSQL

Kafka events are consumed and stored in PostgreSQL.

File:
src/db/postgres_consumer.py

##📁 Repository Structure

equipment-utilization-prototype/
├── data/
│   ├── clips/
│   │   └── test_clip.mp4
│   └── excavator_boxes.csv
├── outputs/
├── src/
│   ├── cv/
│   │   ├── build_tracked_activity_timeline.py
│   │   └── tracked_equipment_events.py
│   ├── db/
│   │   └── postgres_consumer.py
│   ├── processing/
│   │   └── build_tracked_sessions.py
│   ├── streaming/
│   │   ├── kafka_consumer.py
│   │   └── kafka_producer.py
│   ├── tracking/
│   │   └── build_tracks.py
│   └── ui/
│       ├── app.py
│       ├── components.py
│       ├── db.py
│       ├── styles.py
│       └── video_utils.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md


# 🚀 Download & Run the Project

This section explains how to clone the repository, install dependencies, start the required services, and run the full pipeline step by step.

---

## 📥 1. Clone the Repository

```bash
git clone <(https://github.com/Ayama11/equipment-utilization-prototype)>
cd equipment-utilization-prototype
```

# 🧰 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

# 🐳 3. Start Infrastructure Services

```bash
docker compose up -d
docker ps
docker compose down
```

# ▶️ 4. Run the Pipeline
```bash
python src/tracking/build_tracks.py
python src/cv/build_tracked_activity_timeline.py
python src/cv/tracked_equipment_events.py
python src/db/postgres_consumer.py
python src/streaming/kafka_producer.py
python src/processing/build_tracked_sessions.py
streamlit run src/ui/app.py
```

## 📎 Additional Links

- **Technical Report:** [View Report](<(https://drive.google.com/file/d/1ZmLOTIyL_D6pXZLx0RzxEC_LLjvGT7RH/view?usp=drive_link)>)
- **LinkedIn:** [Aya Almalla](<(https://www.linkedin.com/in/aya-almalla)>)
