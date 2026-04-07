
import streamlit as st


def prettify_activity(activity: str) -> str:
    activity = str(activity).strip().upper()
    mapping = {
        "DIGGING": "Digging",
        "SWINGING_LOADING": "Swinging / Loading",
        "DUMPING": "Dumping",
        "WAITING": "Waiting"
    }
    return mapping.get(activity, activity.title().replace("_", " "))


def prettify_motion_source(source: str) -> str:
    source = str(source).strip().lower()
    mapping = {
        "full_machine": "Full Machine Motion",
        "arm_only": "Arm-Only Motion",
        "no_significant_motion": "No Significant Motion"
    }
    return mapping.get(source, source.replace("_", " ").title())


def render_hero():
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-title">Equipment Utilization & Activity Classification Dashboard</div>
        <div class="hero-subtitle">
            Real-time monitoring of construction equipment using computer vision, Kafka streaming, and PostgreSQL analytics
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_card(label: str, value: str, subtext: str = ""):
    with st.container(border=True):
        st.markdown(f'<div class="kpi-label">{label}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{value}</div>', unsafe_allow_html=True)
        if subtext:
            st.markdown(f'<div class="kpi-sub">{subtext}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="kpi-empty">.</div>', unsafe_allow_html=True)


def render_overview_metrics(latest_df):
    if latest_df.empty:
        return

    total_machines = int(latest_df["equipment_id"].nunique())
    active_machines = int((latest_df["current_state"] == "ACTIVE").sum())
    avg_utilization = float(latest_df["utilization_percent"].mean())
    max_tracked = float(latest_df["total_tracked_seconds"].max())
    online_pct = (active_machines / total_machines * 100.0) if total_machines > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Total Machines", str(total_machines))
    with c2:
        render_kpi_card("Currently Active", str(active_machines), f"↗ {online_pct:.0f}% online")
    with c3:
        render_kpi_card("Avg Utilization", f"{avg_utilization:.0f}%")
    with c4:
        render_kpi_card("Max Tracked Time", f"{max_tracked:.2f}s")


def render_status_badge(state: str):
    state = str(state).strip().upper()
    if state == "ACTIVE":
        st.markdown('<span class="status-active">↗ ACTIVE</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-inactive">• INACTIVE</span>', unsafe_allow_html=True)


def render_metric_chip(label: str, value: str, value_class: str = "chip-value"):
    st.markdown(
        f"""
        <div class="metric-chip">
            <div class="metric-chip-label">{label}</div>
            <div class="{value_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_machine_cards(latest_df):
    st.markdown('<div class="section-title">↗ Live Status of Each Machine</div>', unsafe_allow_html=True)

    if latest_df.empty:
        st.warning("No machine data available.")
        return

    rows = latest_df.to_dict("records")

    for i in range(0, len(rows), 2):
        pair = rows[i:i + 2]
        cols = st.columns(2)

        for j, row in enumerate(pair):
            with cols[j]:
                with st.container(border=True):
                    equipment_id = str(row["equipment_id"])
                    current_state = str(row["current_state"]).strip().upper()
                    current_activity = prettify_activity(row["current_activity"])
                    motion_source = prettify_motion_source(row["motion_source"])
                    equipment_class = str(row["equipment_class"]).strip().title()

                    tracked_time = float(row["total_tracked_seconds"])
                    active_time = float(row["total_active_seconds"])
                    idle_time = float(row["total_idle_seconds"])
                    util = max(0.0, min(100.0, float(row["utilization_percent"])))
                    timestamp = str(row["timestamp_str"])

                    top_left, top_right = st.columns([4, 1.2])
                    with top_left:
                        st.markdown(f'<div class="machine-title">{equipment_id}</div>', unsafe_allow_html=True)
                    with top_right:
                        st.markdown(
                            f'<div class="tracked-time">◷ {tracked_time:.2f}s</div>',
                            unsafe_allow_html=True
                        )

                    render_status_badge(current_state)
                    st.markdown('<div class="spacer-12"></div>', unsafe_allow_html=True)

                    g1, g2 = st.columns(2)

                    with g1:
                        render_metric_chip("Current Activity", current_activity)
                        render_metric_chip("Motion Source", motion_source)

                    with g2:
                        render_metric_chip("Equipment Class", equipment_class)
                        render_metric_chip("Utilization", f"{util:.0f}%", value_class="chip-value-accent")

                    p1, p2 = st.columns(2)
                    with p1:
                        st.markdown(f'<div class="time-side-label">Active: {active_time:.2f}s</div>', unsafe_allow_html=True)
                    with p2:
                        st.markdown(
                            f'<div class="time-side-label right-align">Idle: {idle_time:.2f}s</div>',
                            unsafe_allow_html=True
                        )

                    st.progress(util / 100.0)

                    st.markdown(
                        f'<div class="timestamp-text">{timestamp}</div>',
                        unsafe_allow_html=True
                    )