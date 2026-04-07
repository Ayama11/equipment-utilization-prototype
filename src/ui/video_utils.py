
import os
import subprocess
import streamlit as st

ORIGINAL_VIDEO_PATH = "outputs/verified_boxes_fin.mp4"
WEB_VIDEO_PATH = "outputs/verified_boxes_fin_web.mp4"


def ensure_web_video():
    if os.path.exists(WEB_VIDEO_PATH):
        return WEB_VIDEO_PATH

    if not os.path.exists(ORIGINAL_VIDEO_PATH):
        return None

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", ORIGINAL_VIDEO_PATH,
        "-vcodec", "libx264",
        "-acodec", "aac",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        WEB_VIDEO_PATH
    ]

    try:
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return WEB_VIDEO_PATH
    except Exception:
        return None


def render_video_panel():
    st.markdown('<div class="section-title">◧ Processed Video Feed</div>', unsafe_allow_html=True)
    st.markdown('<div class="video-panel">', unsafe_allow_html=True)

    video_path = ensure_web_video()

    if video_path and os.path.exists(video_path):
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        st.video(video_bytes)
    else:
        st.info("Annotated video stream with CV detection")
        st.caption("Generate outputs/verified_boxes_web.mp4 using ffmpeg for browser playback.")

    st.markdown('</div>', unsafe_allow_html=True)