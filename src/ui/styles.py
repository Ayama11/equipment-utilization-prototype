

import streamlit as st


def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stApp, .stMarkdown, .stDataFrame, .stMetric {
            font-family: 'Inter', sans-serif !important;
            background: #030712;
            color: #f9fafb;
        }

        .main {
            background: #030712;
        }

        .block-container {
            max-width: 1460px;
            padding-top: 1.7rem;
            padding-bottom: 2.4rem;
        }

        .hero-wrap {
            background: linear-gradient(180deg, #07122a 0%, #08162f 100%);
            border: 1px solid rgba(96, 165, 250, 0.16);
            border-radius: 22px;
            padding: 30px 34px;
            margin-bottom: 26px;
            box-shadow: 0 18px 40px rgba(0,0,0,0.24);
        }

        .hero-title {
            font-size: 2.55rem;
            font-weight: 800;
            color: #eff6ff;
            line-height: 1.15;
            margin-bottom: 0.55rem;
            letter-spacing: -0.03em;
        }

        .hero-subtitle {
            color: #94a3b8;
            font-size: 1.04rem;
            line-height: 1.65;
            font-weight: 500;
            max-width: 950px;
        }

        .section-title {
            font-size: 1.28rem;
            font-weight: 800;
            color: #f8fafc;
            margin: 1.1rem 0 1rem 0;
            letter-spacing: -0.01em;
        }

        .panel-title {
            font-size: 1.12rem;
            font-weight: 750;
            color: #f8fafc;
            margin-bottom: 0.9rem;
            letter-spacing: -0.01em;
        }

        .kpi-label {
            color: #94a3b8;
            font-size: 0.92rem;
            font-weight: 600;
            margin-bottom: 0.7rem;
            line-height: 1.3;
        }

        .kpi-value {
            color: #f8fafc;
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: 0.32rem;
            letter-spacing: -0.03em;
        }

        .kpi-sub {
            color: #22c55e;
            font-size: 0.9rem;
            font-weight: 650;
            line-height: 1.3;
        }

        .kpi-empty {
            color: transparent;
            font-size: 0.9rem;
            line-height: 1.3;
        }

        .machine-title {
            font-size: 1.42rem;
            font-weight: 800;
            color: #f8fafc;
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin-bottom: 0.05rem;
        }

        .tracked-time {
            color: #9ca3af;
            font-size: 0.96rem;
            text-align: right;
            margin-top: 0.18rem;
            font-weight: 600;
            line-height: 1.25;
        }

        .metric-chip {
            background: linear-gradient(180deg, rgba(10,22,45,0.95) 0%, rgba(11,24,49,0.92) 100%);
            border: 1px solid rgba(148,163,184,0.12);
            border-radius: 16px;
            padding: 14px 15px;
            min-height: 86px;
            margin-bottom: 12px;
        }

        .metric-chip-label {
            color: #94a3b8;
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.45rem;
            line-height: 1.3;
        }

        .chip-value {
            color: #f8fafc;
            font-size: 1.05rem;
            font-weight: 750;
            line-height: 1.4;
            word-break: break-word;
        }

        .chip-value-accent {
            color: #60a5fa;
            font-size: 1.1rem;
            font-weight: 800;
            line-height: 1.35;
        }

        .timestamp-text {
            color: #6b7280;
            font-size: 0.92rem;
            margin-top: 0.65rem;
            font-weight: 500;
            line-height: 1.3;
        }

        .time-side-label {
            color: #cbd5e1;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.28rem;
            line-height: 1.3;
        }

        .right-align {
            text-align: right;
        }

        .status-active {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 10px;
            background: rgba(16,185,129,0.14);
            color: #34d399;
            border: 1px solid rgba(16,185,129,0.24);
            font-size: 0.93rem;
            font-weight: 750;
            letter-spacing: 0.01em;
        }

        .status-inactive {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 10px;
            background: rgba(245,158,11,0.14);
            color: #fbbf24;
            border: 1px solid rgba(245,158,11,0.24);
            font-size: 0.93rem;
            font-weight: 750;
            letter-spacing: 0.01em;
        }

        .small-note {
            color: #6b7280;
            font-size: 0.92rem;
            font-weight: 500;
            line-height: 1.4;
        }

        .spacer-12 {
            height: 12px;
        }

        .stMarkdown p, .stMarkdown div, label, span {
            font-size: 1rem;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, #08162b 0%, #0b1831 100%);
            border: 1px solid rgba(148,163,184,0.14);
            border-radius: 18px;
            padding: 14px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.16);
        }

        div[data-testid="stVerticalBlock"] div[data-testid="stProgress"] > div {
            background-color: rgba(71,85,105,0.34);
            border-radius: 999px;
        }

        div[data-testid="stProgress"] div[role="progressbar"] {
            background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
            border-radius: 999px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(148,163,184,0.10);
        }

        [data-testid="stSidebar"] {
            background: #111827;
        }

        div[data-testid="stHorizontalBlock"] > div {
            align-self: stretch;
        }

        @media (max-width: 1100px) {
            .hero-title {
                font-size: 2rem;
            }

            .hero-subtitle {
                font-size: 0.98rem;
            }

            .machine-title {
                font-size: 1.25rem;
            }

            .kpi-value {
                font-size: 1.72rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)