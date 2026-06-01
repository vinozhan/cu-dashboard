"""Shared styling constants and CSS for the audit dashboard."""

# Brand colors
PRIMARY = "#009ceb"
PRIMARY_DARK = "#0077b6"
PRIMARY_LIGHT = "#e8f4fc"
ACCENT = "#00b4d8"
TEXT_DARK = "#1a1a2e"
TEXT_MUTED = "#5a6677"
WHITE = "#ffffff"
BG_LIGHT = "#f0f8ff"

# Chart colors — high contrast, colorblind-friendly, easy to distinguish.
# Brand blue is used for UI chrome; charts use a diverse palette for readability.
PLOTLY_COLORS = [
    "#4e79a7",  # steel blue
    "#f28e2b",  # warm orange
    "#e15759",  # coral red
    "#76b7b2",  # teal
    "#59a14f",  # green
    "#edc948",  # gold
    "#b07aa1",  # muted purple
    "#ff9da7",  # soft pink
    "#9c755f",  # brown
    "#bab0ac",  # warm grey
]

PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, sans-serif", color=TEXT_DARK),
        title=dict(font=dict(size=18, color=PRIMARY_DARK)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=PLOTLY_COLORS,
        hoverlabel=dict(
            bgcolor=PRIMARY_DARK,
            font_size=13,
            font_color=WHITE,
        ),
    )
)


def apply_custom_css():
    """Inject custom CSS to style the Streamlit app with brand colors."""
    import streamlit as st

    st.markdown("""
    <style>
        /* Header bar */
        header[data-testid="stHeader"] {
            background: linear-gradient(90deg, #121536 0%, #1b1e42 45%, #242b57 100%);
            border-bottom: 1px solid rgba(255,255,255,0.08);
            backdrop-filter: saturate(1.2) blur(6px);
            box-shadow: 0 4px 14px rgba(8, 12, 40, 0.35);
            position: relative;
        }
        /* Header notification bell (visual nav affordance) */
        header[data-testid="stHeader"]::after {
            content: "";
            position: absolute;
            top: 10px;
            right: 120px;
            width: 18px;
            height: 18px;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23eaf5ff'%3E%3Cpath d='M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 1 0-14 0v5l-2 2v1h18v-1l-2-2Z'/%3E%3C/svg%3E");
            background-size: contain;
            background-repeat: no-repeat;
            opacity: 0.95;
            pointer-events: none;
            z-index: 5;
            filter: drop-shadow(0 1px 3px rgba(0,0,0,0.35));
        }
        header[data-testid="stHeader"]::before {
            content: "";
            position: absolute;
            top: 8px;
            right: 116px;
            width: 7px;
            height: 7px;
            background: #ff4d6d;
            border: 1px solid rgba(255,255,255,0.85);
            border-radius: 50%;
            z-index: 6;
            pointer-events: none;
        }
        /* Header toolbar buttons (Deploy, 3-dots menu) */
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] [data-testid="stToolbar"] button {
            color: rgba(255,255,255,0.82);
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        header[data-testid="stHeader"] button:hover,
        header[data-testid="stHeader"] [data-testid="stToolbar"] button:hover {
            color: #ffffff;
            background: rgba(255,255,255,0.16);
        }
        /* Toolbar icons visibility */
        header[data-testid="stHeader"] [data-testid="stToolbar"] {
            color: rgba(255,255,255,0.82);
        }
        header[data-testid="stHeader"] [data-testid="stToolbar"] svg {
            fill: rgba(255,255,255,0.82);
        }
        header[data-testid="stHeader"] [data-testid="stToolbar"] svg:hover {
            fill: #ffffff;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #161a3d 0%, #1b1e42 38%, #1e224a 100%);
            border-right: 1px solid rgba(255,255,255,0.12);
            box-shadow: 4px 0 20px rgba(7, 10, 34, 0.35);
            position: relative;
        }
        
        /* Collapse sidebar button — style for dark bg */
        button[data-testid="stSidebarCollapseButton"] {
            color: rgba(255,255,255,0.78);
            border-radius: 8px;
            transition: all 0.2s ease;
            position: absolute;
            top: 14px;
            right: 14px;
            z-index: 3;
        }
        button[data-testid="stSidebarCollapseButton"]:hover {
            color: #ffffff;
            background: rgba(255,255,255,0.14);
        }
        /* Expand sidebar button — Material icon with inline color on dark header */
        [data-testid="stIconMaterial"] {
            color: rgba(255,255,255,0.7);
        }
        [data-testid="stIconMaterial"]:hover {
            color: #ffffff;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #ffffff;
        }
        /* Sidebar text and labels */
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] .stMarkdown {
            color: rgba(255,255,255,0.85);
        }
        /* Sidebar nav links */
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            color: rgba(255,255,255,0.78);
            border-radius: 10px;
            margin: 4px 10px;
            padding: 9px 12px;
            border: 1px solid transparent;
            transition: all 0.2s ease;
            font-weight: 500;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            color: #ffffff;
            background: rgba(255,255,255,0.08);
            border-color: rgba(255,255,255,0.16);
            transform: translateX(2px);
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            color: #ffffff;
            background: linear-gradient(90deg, rgba(0,156,235,0.42) 0%, rgba(0,180,216,0.24) 100%);
            border-color: rgba(0,180,216,0.45);
            box-shadow: inset 2px 0 0 #90e0ef;
        }


        /* Metric cards */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #e8f4fc 0%, #ffffff 100%);
            border: 1px solid #009ceb30;
            border-left: 4px solid #009ceb;
            border-radius: 8px;
            padding: 12px 16px;
        }
        div[data-testid="stMetric"] label {
            color: #5a6677;
            font-size: 0.85rem;
            font-weight: 500;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #0077b6;
            font-weight: 700;
        }

        /* Tabs */
        button[data-baseweb="tab"] {
            font-weight: 600;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            border-bottom-color: #009ceb;
            color: #009ceb;
        }

        /* Data tables */
        div[data-testid="stDataFrame"] {
            border: 1px solid #009ceb20;
            border-radius: 8px;
        }

        /* Dividers */
        hr {
            border-color: #009ceb30;
        }

        /* Page title styling */
        .brand-title {
            color: #0077b6;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-subtitle {
            color: #5a6677;
            font-size: 1rem;
            margin-bottom: 1rem;
        }
        .brand-header-bar {
            height: 4px;
            background: linear-gradient(90deg, #009ceb 0%, #00b4d8 50%, #90e0ef 100%);
            border-radius: 2px;
            margin-bottom: 1.5rem;
        }

        /* Info/success/warning boxes */
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }

        /* Download button */
        button[data-testid="stDownloadButton"] {
            border-radius: 6px;
        }

        /* File uploader: improve icon/text contrast and button clarity */
        [data-testid="stFileUploader"] > div {
            background: #f4f8ff;
            border: 1px solid #b9d9f2;
            border-radius: 12px;
        }
        [data-testid="stFileUploader"] section {
            border: 1px dashed #7dbbe6;
            border-radius: 12px;
            background: #f8fbff;
        }
        [data-testid="stFileUploader"] button {
            background: #ffffff;
            color: #005f9e;
            border: 1px solid #86c5ee;
            border-radius: 10px;
            font-weight: 600;
        }
        [data-testid="stFileUploader"] button:hover {
            background: #eaf5ff;
            color: #004f84;
            border-color: #5faee2;
        }
        [data-testid="stFileUploader"] svg {
            fill: #009ceb !important;
            color: #009ceb !important;
        }
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span,
        [data-testid="stFileUploader"] p {
            color: #4b5b70 !important;
        }
    </style>
    """, unsafe_allow_html=True)


def sidebar_branding():
    """Inject CSS to render branded title at the very top of the sidebar, above nav."""
    import streamlit as st

    st.markdown("""
    <style>
        /* Sidebar branding above navigation */
        section[data-testid="stSidebar"]::before {
            content: "Audit Dashboard";
            display: block;
            font-size: 1.3rem;
            font-weight: 700;
            color: #ffffff;
            padding: 20px 24px 4px 64px;
            line-height: 1.2;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='26' height='26' viewBox='0 0 26 26'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0%25' stop-color='%23009ceb'/%3E%3Cstop offset='100%25' stop-color='%2300b4d8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect x='1' y='1' width='24' height='24' rx='7' fill='url(%23g)'/%3E%3Cpath d='M7.2 16.5V9.5h3.1c1.8 0 2.9 1.1 2.9 2.6 0 1.6-1.1 2.7-2.9 2.7H9.4v1.7H7.2zm2.2-3.5h0.8c0.7 0 1.1-0.4 1.1-0.9 0-0.5-0.4-0.9-1.1-0.9H9.4V13zm6.4 3.5V9.5h2.1v5.1h2.9v1.9h-5z' fill='white'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-size: 26px 26px;
            background-position: 24px 20px;
        }
        section[data-testid="stSidebar"]::after {
            content: "Optimization & Planning";
            display: block;
            font-size: 0.75rem;
            color: rgba(255,255,255,0.6);
            padding: 0 24px 12px 64px;
            border-bottom: 1px solid rgba(255,255,255,0.15);
            margin-bottom: 8px;
        }
    </style>
    """, unsafe_allow_html=True)


def page_header(title, subtitle=""):
    """Render a branded page header."""
    import streamlit as st

    apply_custom_css()
    sidebar_branding()
    if title:
        st.markdown(f'<div class="brand-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="brand-subtitle">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-header-bar"></div>', unsafe_allow_html=True)


def style_plotly_fig(fig):
    """Apply brand styling to a Plotly figure."""
    layout_updates = dict(
        font=dict(family="Inter, sans-serif", color=TEXT_DARK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=PRIMARY_DARK, font_size=13, font_color=WHITE),
        legend=dict(
            bgcolor="rgba(232,244,252,0.7)",
            bordercolor=PRIMARY,
            borderwidth=1,
            font=dict(size=12),
        ),
    )
    # Only style title if figure already has one set — avoids "Undefined"
    if fig.layout.title and fig.layout.title.text:
        layout_updates["title_font"] = dict(size=18, color=PRIMARY_DARK)
    fig.update_layout(**layout_updates)
    fig.update_xaxes(gridcolor="#e8f4fc", zerolinecolor="rgba(0,156,235,0.25)")
    fig.update_yaxes(gridcolor="#e8f4fc", zerolinecolor="rgba(0,156,235,0.25)")
    return fig
