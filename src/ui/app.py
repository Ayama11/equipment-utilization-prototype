

import altair as alt
import pandas as pd
import streamlit as st

from db import load_dashboard_data
from styles import inject_css
from components import render_hero, render_overview_metrics, render_machine_cards
from video_utils import render_video_panel

st.set_page_config(
    page_title="Equipment Monitoring Dashboard",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="collapsed"
)

inject_css()


@st.cache_data(ttl=2)
def get_data():
    return load_dashboard_data()


def prettify_activity_name(activity: str) -> str:
    activity = str(activity).strip().upper()
    mapping = {
        "DIGGING": "DIGGING",
        "SWINGING_LOADING": "SWINGING_LOADING",
        "DUMPING": "DUMPING",
        "WAITING": "WAITING"
    }
    return mapping.get(activity, activity)


def build_recent_events_table(recent_df):
    rows = []
    if recent_df.empty:
        return rows

    prev_activity_by_machine = {}
    prev_state_by_machine = {}
    high_util_flag_by_machine = {}

    ordered = recent_df.sort_values("id", ascending=True)

    for _, row in ordered.iterrows():
        machine = row["equipment_id"]
        current_activity = str(row["current_activity"]).strip()
        current_state = str(row["current_state"]).strip()
        util = float(row["utilization_percent"])

        event_name = "Telemetry Update"
        details = f"Activity={current_activity}"
        priority = 0

        if machine in prev_activity_by_machine and prev_activity_by_machine[machine] != current_activity:
            event_name = "Activity Changed"
            details = f"{prev_activity_by_machine[machine]} → {current_activity}"
            priority = 3

        elif machine in prev_state_by_machine and prev_state_by_machine[machine] != current_state:
            event_name = "State Changed"
            details = f"{prev_state_by_machine[machine]} → {current_state}"
            priority = 2

        else:
            prev_high = high_util_flag_by_machine.get(machine, False)
            current_high = util >= 85.0

            if current_high and not prev_high:
                event_name = "High Utilization"
                details = f"Utilization reached {util:.2f}%"
                priority = 1
            else:
                event_name = "Telemetry Update"
                details = f"Activity={current_activity}, Utilization={util:.2f}%"
                priority = 0

            high_util_flag_by_machine[machine] = current_high

        rows.append({
            "Timestamp": row["timestamp_str"],
            "Equipment ID": machine,
            "Event": event_name,
            "Details": details,
            "_priority": priority,
            "_id": row["id"]
        })

        prev_activity_by_machine[machine] = current_activity
        prev_state_by_machine[machine] = current_state

        if machine not in high_util_flag_by_machine:
            high_util_flag_by_machine[machine] = util >= 85.0

    rows = sorted(rows, key=lambda x: (x["_priority"], x["_id"]), reverse=True)
    rows = rows[:10]

    for row in rows:
        row.pop("_priority", None)
        row.pop("_id", None)

    return rows


def style_event_name(val):
    val_str = str(val).strip().lower()

    base = (
        "font-weight: 700; "
        "border-radius: 8px; "
        "padding: 4px 10px; "
        "text-align: center;"
    )

    if val_str == "activity changed":
        return base + "color: #34d399; background-color: rgba(16,185,129,0.16);"
    elif val_str == "state changed":
        return base + "color: #60a5fa; background-color: rgba(59,130,246,0.16);"
    elif val_str == "high utilization":
        return base + "color: #fbbf24; background-color: rgba(245,158,11,0.16);"
    else:
        return base + "color: #d1d5db; background-color: rgba(107,114,128,0.16);"


def style_recent_events_table(rows):
    df = pd.DataFrame(rows)

    if df.empty:
        return df

    styled = (
        df.style
        .map(style_event_name, subset=["Event"])
        .set_table_styles([
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#161b29"),
                    ("color", "#9ca3af"),
                    ("font-size", "15px"),
                    ("font-weight", "600"),
                    ("border-bottom", "1px solid #243046"),
                    ("padding", "12px"),
                    ("text-align", "left"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("background-color", "#0b1220"),
                    ("color", "#f9fafb"),
                    ("font-size", "15px"),
                    ("border-bottom", "1px solid #1f2937"),
                    ("padding", "12px"),
                ],
            },
            {
                "selector": "tbody tr:hover td",
                "props": [
                    ("background-color", "#111827"),
                ],
            },
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("width", "100%"),
                    ("border-radius", "14px"),
                    ("overflow", "hidden"),
                ],
            },
        ])
        .hide(axis="index")
    )

    return styled


def prepare_trend_chart(trend_df: pd.DataFrame):
    if trend_df.empty:
        return None

    plot_df = trend_df.copy()
    plot_df["utilization_percent"] = plot_df["utilization_percent"].astype(float)
    plot_df["time_label"] = plot_df["timestamp_str"].astype(str)

    if len(plot_df) > 16:
        step = max(1, len(plot_df) // 16)
        plot_df = plot_df.iloc[::step].copy()

    line = alt.Chart(plot_df).mark_line(
        color="#3b82f6",
        strokeWidth=3,
        point=alt.OverlayMarkDef(size=85, filled=True, color="#3b82f6")
    ).encode(
        x=alt.X(
            "time_label:N",
            title="Timestamp",
            axis=alt.Axis(
                labelColor="#9ca3af",
                labelFontSize=14,
                titleColor="#cbd5e1",
                domainColor="#6b7280",
                tickColor="#6b7280",
                labelAngle=0
            )
        ),
        y=alt.Y(
            "utilization_percent:Q",
            title="Utilization %",
            scale=alt.Scale(domain=[0, 100]),
            axis=alt.Axis(
                labelColor="#9ca3af",
                labelFontSize=14,
                titleColor="#cbd5e1",
                grid=True,
                gridColor="#23314f",
                domainColor="#6b7280"
            )
        ),
        tooltip=[
            alt.Tooltip("time_label:N", title="Timestamp"),
            alt.Tooltip("utilization_percent:Q", title="Utilization", format=".2f")
        ]
    ).properties(
        height=320,
        background="#0a162d"
    )

    return line.configure_view(stroke=None)


def prepare_activity_chart(activity_df: pd.DataFrame):
    if activity_df.empty:
        return None

    plot_df = activity_df.copy()
    plot_df["current_activity"] = plot_df["current_activity"].astype(str).str.strip().str.upper()
    plot_df["display_activity"] = plot_df["current_activity"].apply(prettify_activity_name)

    activity_order = ["DIGGING", "SWINGING_LOADING", "DUMPING", "WAITING"]
    plot_df["display_activity"] = pd.Categorical(
        plot_df["display_activity"],
        categories=activity_order,
        ordered=True
    )
    plot_df = plot_df.sort_values("display_activity")

    color_map = {
        "DIGGING": "#3b82f6",
        "SWINGING_LOADING": "#10b981",
        "DUMPING": "#f59e0b",
        "WAITING": "#6b7280"
    }

    chart = alt.Chart(plot_df).mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X(
            "display_activity:N",
            sort=activity_order,
            title="Activity",
            axis=alt.Axis(
                labelColor="#9ca3af",
                labelFontSize=14,
                titleColor="#cbd5e1",
                domainColor="#6b7280",
                tickColor="#6b7280",
                labelAngle=0
            )
        ),
        y=alt.Y(
            "count:Q",
            title="Count",
            axis=alt.Axis(
                labelColor="#9ca3af",
                labelFontSize=14,
                titleColor="#cbd5e1",
                grid=True,
                gridColor="#23314f",
                domainColor="#6b7280"
            )
        ),
        color=alt.Color(
            "display_activity:N",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values())
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip("display_activity:N", title="Activity"),
            alt.Tooltip("count:Q", title="Count")
        ]
    ).properties(
        height=320,
        background="#0a162d"
    )

    return chart.configure_view(stroke=None)


def load_idle_sessions_csv(csv_path="outputs/tracked_idle_sessions.csv"):
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    expected_cols = ["track_id", "start_sec", "end_sec", "duration_sec"]
    for col in expected_cols:
        if col not in df.columns:
            return pd.DataFrame()

    df["track_id"] = pd.to_numeric(df["track_id"], errors="coerce")
    df["start_sec"] = pd.to_numeric(df["start_sec"], errors="coerce")
    df["end_sec"] = pd.to_numeric(df["end_sec"], errors="coerce")
    df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce")

    df = df.dropna(subset=["track_id", "start_sec", "end_sec", "duration_sec"]).copy()
    df["track_id"] = df["track_id"].astype(int)

    df = df.sort_values(["track_id", "start_sec"], ascending=[True, True]).reset_index(drop=True)
    return df


def canonical_equipment_id_from_track(track_id: int) -> str:
    return f"EX-{int(track_id):03d}"


def format_seconds_as_clock(sec):
    sec = float(sec)
    minutes = int(sec // 60)
    seconds = sec % 60
    return f"{minutes:02d}:{seconds:05.2f}"


def render_idle_sessions_section(latest_df: pd.DataFrame):
    idle_df = load_idle_sessions_csv()

    st.markdown('<div class="section-title">◴ Idle Sessions / Dwell Time</div>', unsafe_allow_html=True)

    with st.container(border=True):
        if idle_df.empty:
            st.info("No idle sessions available.")
            return

        latest_lookup = {}
        if latest_df is not None and not latest_df.empty:
            latest_copy = latest_df.copy()
            latest_copy["equipment_id"] = latest_copy["equipment_id"].astype(str).str.strip()
            for _, row in latest_copy.iterrows():
                latest_lookup[row["equipment_id"]] = {
                    "total_idle_seconds": float(row["total_idle_seconds"]),
                    "total_tracked_seconds": float(row["total_tracked_seconds"]),
                    "utilization_percent": float(row["utilization_percent"]),
                    "current_state": str(row["current_state"]).strip(),
                    "current_activity": str(row["current_activity"]).strip(),
                }

        track_ids = sorted(idle_df["track_id"].unique().tolist())

        for track_id in track_ids:
            equipment_id = canonical_equipment_id_from_track(track_id)
            machine_sessions = idle_df[idle_df["track_id"] == track_id].copy()

            st.markdown(
                f'<div class="panel-title">Machine: {equipment_id}</div>',
                unsafe_allow_html=True
            )

            db_total_idle = latest_lookup.get(
                equipment_id,
                {}
            ).get("total_idle_seconds", float(machine_sessions["duration_sec"].sum()))

            longest_idle = float(machine_sessions["duration_sec"].max()) if not machine_sessions.empty else 0.0
            idle_sessions_count = len(machine_sessions)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Idle Sessions", int(idle_sessions_count))
            with c2:
                st.metric("Total Idle Time", f"{db_total_idle:.2f}s")
            with c3:
                st.metric("Longest Idle Session", f"{longest_idle:.2f}s")

            display_df = machine_sessions.copy()
            display_df["Equipment ID"] = equipment_id
            display_df["Start"] = display_df["start_sec"].apply(format_seconds_as_clock)
            display_df["End"] = display_df["end_sec"].apply(format_seconds_as_clock)
            display_df["Duration (s)"] = display_df["duration_sec"].round(2)

            display_df = display_df[[
                "Equipment ID",
                "Start",
                "End",
                "Duration (s)"
            ]]

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("<br>", unsafe_allow_html=True)


try:
    latest_df, recent_df, trend_df, activity_df = get_data()
except Exception as e:
    st.error(f"Failed to load dashboard data: {e}")
    st.stop()

render_hero()
render_overview_metrics(latest_df)
render_machine_cards(latest_df)

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown('<div class="panel-title">↗ Utilization Trend</div>', unsafe_allow_html=True)
        chart = prepare_trend_chart(trend_df)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No utilization trend data available.")

with col2:
    with st.container(border=True):
        st.markdown('<div class="panel-title">↘ Activity Distribution</div>', unsafe_allow_html=True)
        chart = prepare_activity_chart(activity_df)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No activity distribution data available.")

st.markdown('<div class="section-title">◷ Recent Events</div>', unsafe_allow_html=True)
with st.container(border=True):
    recent_rows = build_recent_events_table(recent_df)
    if recent_rows:
        styled_table = style_recent_events_table(recent_rows)
        st.dataframe(styled_table, use_container_width=True)
    else:
        st.info("No recent events available.")

render_idle_sessions_section(latest_df)

render_video_panel()

st.markdown("---")
st.markdown(
    '<div class="small-note">Computer Vision → Kafka → PostgreSQL → Streamlit Dashboard</div>',
    unsafe_allow_html=True
)