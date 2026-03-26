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
            background: #1b1e42;
        }
        /* Header toolbar buttons (Deploy, 3-dots menu) */
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] [data-testid="stToolbar"] button {
            color: rgba(255,255,255,0.7);
        }
        header[data-testid="stHeader"] button:hover,
        header[data-testid="stHeader"] [data-testid="stToolbar"] button:hover {
            color: #ffffff;
            background: rgba(255,255,255,0.1);
        }
        /* Toolbar icons visibility */
        header[data-testid="stHeader"] [data-testid="stToolbar"] {
            color: rgba(255,255,255,0.7);
        }
        header[data-testid="stHeader"] [data-testid="stToolbar"] svg {
            fill: rgba(255,255,255,0.7);
        }
        header[data-testid="stHeader"] [data-testid="stToolbar"] svg:hover {
            fill: #ffffff;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #1b1e42;
            border-right: 1px solid rgba(255,255,255,0.1);
        }
        
        /* Collapse sidebar button — style for dark bg */
        button[data-testid="stSidebarCollapseButton"] {
            color: rgba(255,255,255,0.6);
        }
        button[data-testid="stSidebarCollapseButton"]:hover {
            color: #ffffff;
            background: rgba(255,255,255,0.1);
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
            color: rgba(255,255,255,0.75);
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
            color: #ffffff;
            background: rgba(0,156,235,0.2);
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
            padding: 20px 24px 4px 24px;
            line-height: 1.2;
        }
        section[data-testid="stSidebar"]::after {
            content: "Optimization & Planning";
            display: block;
            font-size: 0.75rem;
            color: rgba(255,255,255,0.6);
            padding: 0 24px 12px 24px;
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
