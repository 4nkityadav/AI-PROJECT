"""
styles.py — Class Pilot Design System & HTML Renderers.
Inspired by modern Uiverse.io UI designs:
- Subtle glowing ambient mesh background with modern micro-dot grid
- Glassmorphic floating navigation header with high-tech SVG vector logo
- Multi-layered borders, card elevations, and tactile hover animations
- Dynamic Google Fonts: Outfit (Headings), Plus Jakarta Sans (Body), JetBrains Mono (Metrics)
- High-contrast Theory vs Lab lesson cards with 3D pop hover states
- Distinct vibrant button color schemes for primary actions, navigation, and export formats
- Pure, clean HTML/SVG with zero raw code leaks
"""

# Theory vs Lab color palettes (Vibrant, high-contrast, modern academic SaaS)
THEORY_THEME = {
    "border": "#3B82F6",       # Vibrant Royal Blue
    "bg": "linear-gradient(135deg, #EFF6FF 0%, #E0E7FF 100%)",
    "text": "#1E3A8A",          # Deep Oxford Blue
    "badge_bg": "#DBEAFE",     # Pill Light Blue
    "badge_text": "#1D4ED8",   # Primary Blue Text
    "label": "THEORY",
}

LAB_THEME = {
    "border": "#10B981",       # Emerald Green
    "bg": "linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)",
    "text": "#064E3B",          # Deep Forest Green
    "badge_bg": "#D1FAE5",     # Pill Mint
    "badge_text": "#047857",   # Dark Emerald Text
    "label": "LAB",
}

# 8 Curated, Dignified Subject Sub-Themes (Deterministic by subject code)
COURSE_PALETTES = [
    {"border": "#3B82F6", "bg": "linear-gradient(135deg, #EFF6FF 0%, #E0E7FF 100%)", "text": "#1E3A8A", "badge": "#DBEAFE"},
    {"border": "#6366F1", "bg": "linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%)", "text": "#312E81", "badge": "#E0E7FF"},
    {"border": "#0D9488", "bg": "linear-gradient(135deg, #F0FDFA 0%, #CCFBF1 100%)", "text": "#134E48", "badge": "#CCFBF1"},
    {"border": "#8B5CF6", "bg": "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", "text": "#4C1D95", "badge": "#EDE9FE"},
    {"border": "#0284C7", "bg": "linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%)", "text": "#0C4A6E", "badge": "#E0F2FE"},
    {"border": "#D97706", "bg": "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)", "text": "#78350F", "badge": "#FEF3C7"},
    {"border": "#059669", "bg": "linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)", "text": "#064E3B", "badge": "#D1FAE5"},
    {"border": "#EC4899", "bg": "linear-gradient(135deg, #FDF2F8 0%, #FCE7F3 100%)", "text": "#831843", "badge": "#FCE7F3"},
]


def get_subject_theme(subject_code: str, is_lab: bool = False) -> dict:
    """Return appropriate color theme for a subject session."""
    if is_lab:
        return LAB_THEME
    h = 0
    for char in subject_code:
        h = (h * 31 + ord(char)) & 0xFFFFFFFF
    idx = h % len(COURSE_PALETTES)
    theme = dict(COURSE_PALETTES[idx])
    theme["badge_bg"] = theme["badge"]
    theme["badge_text"] = theme["text"]
    theme["label"] = "THEORY"
    return theme


def get_subject_color(subject_code: str) -> str:
    """Return primary border color for subject."""
    return get_subject_theme(subject_code)["border"]


def svg_icon(name: str, size: int = 14, color: str = "currentColor", extra_class: str = "") -> str:
    """Safe glyph renderer using clean Unicode symbols with inline font styles."""
    mapping = {
        "compass": "✈",
        "check": "✓",
        "alert_triangle": "⚠",
        "info": "ℹ",
        "map_pin": "📍",
    }
    sym = mapping.get(name, "•")
    return f'<span class="{extra_class}" style="font-size:{size}px; line-height:1; vertical-align:middle; color:{color}; display:inline-block; font-weight:bold;">{sym}</span>'


# ── Complete Modern Uiverse-Inspired SaaS Design System CSS ──
CUSTOM_CSS = """
<style>
/* ── Typography: Outfit (Headings), Plus Jakarta Sans (Body), JetBrains Mono (Code) ── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ── Uiverse Theme Tokens ── */
:root {
    --brand-indigo: #4F46E5;
    --brand-violet: #7C3AED;
    --brand-cyan: #06B6D4;
    --brand-emerald: #10B981;
    --brand-rose: #E11D48;
    --brand-amber: #F59E0B;

    --canvas-bg: #F8FAFD;
    --surface-bg: rgba(255, 255, 255, 0.95);
    --surface-card: #FFFFFF;
    --surface-subtle: #F1F5F9;

    --border-subtle: #E2E8F0;
    --border-hover: #CBD5E1;
    --border-active: #94A3B8;
    --border-glow: rgba(99, 102, 241, 0.35);

    --text-primary: #0F172A;
    --text-secondary: #334155;
    --text-muted: #64748B;

    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-full: 9999px;
}

/* ── Global Styles & Ambient Canvas Background ── */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--canvas-bg) !important;
    background-image: 
        radial-gradient(rgba(148, 163, 184, 0.22) 1px, transparent 1px),
        radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.08) 0px, transparent 40%),
        radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.07) 0px, transparent 35%),
        radial-gradient(at 50% 100%, rgba(225, 29, 72, 0.04) 0px, transparent 45%) !important;
    background-size: 24px 24px, 100% 100%, 100% 100%, 100% 100% !important;
    background-attachment: fixed !important;
    color: var(--text-secondary) !important;
    -webkit-font-smoothing: antialiased;
}

/* ── Hide Streamlit Sidebar ── */
section[data-testid="stSidebar"],
div[data-testid="collapsedControl"] {
    display: none !important;
}

/* ── Container Max Width & Padding ── */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1420px !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ── Uiverse Floating Glassmorphic Navbar ── */
.cp-header {
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: var(--radius-lg);
    padding: 1.0rem 1.6rem;
    margin-bottom: 1.4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 
        0 4px 6px -1px rgba(0, 0, 0, 0.03),
        0 20px 25px -5px rgba(15, 23, 42, 0.05),
        0 0 0 1px rgba(255, 255, 255, 0.9) inset;
    flex-wrap: wrap;
    gap: 14px;
    position: relative;
    overflow: hidden;
}

/* Radiant top accent bar on the navbar */
.cp-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3.5px;
    background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 33%, #06B6D4 66%, #10B981 100%);
}

.cp-brand-group {
    display: flex;
    align-items: center;
    gap: 16px;
}

/* Bespoke Vector Logo Badge */
.cp-logo-badge {
    width: 46px;
    height: 46px;
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #06B6D4 100%);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 
        0 4px 14px rgba(79, 70, 229, 0.40),
        inset 0 1px 0 rgba(255, 255, 255, 0.35);
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    cursor: default;
}

.cp-logo-badge:hover {
    transform: rotate(6deg) scale(1.08);
}

.cp-brand-text {
    display: flex;
    flex-direction: column;
}

.cp-brand-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 1.42rem;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.15;
    letter-spacing: -0.03em;
    display: flex;
    align-items: center;
    gap: 8px;
}

.cp-brand-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: var(--radius-full);
    background: linear-gradient(135deg, #EEF2FF, #E0E7FF);
    color: #4338CA;
    border: 1px solid #C7D2FE;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.cp-brand-subtitle {
    font-size: 0.76rem;
    font-weight: 500;
    color: var(--text-muted);
    letter-spacing: 0.01em;
}

.cp-header-status {
    display: flex;
    align-items: center;
    gap: 12px;
}

/* Uiverse Pulsing Radar Status Pills */
.cp-status-pill {
    padding: 7px 16px;
    border-radius: var(--radius-full);
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.01em;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.cp-status-ready {
    background: #ECFDF5;
    color: #047857;
    border: 1px solid #A7F3D0;
}

.cp-status-neutral {
    background: #F8FAFC;
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
}

.cp-status-alert {
    background: #FEF2F2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}

/* Pulsing radar dots */
.cp-radar-dot {
    position: relative;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
}

.cp-radar-dot-green {
    background-color: #10B981;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: uiverse-ripple 1.8s infinite cubic-bezier(0.66, 0, 0, 1);
}

.cp-radar-dot-red {
    background-color: #EF4444;
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
    animation: uiverse-ripple 1.4s infinite cubic-bezier(0.66, 0, 0, 1);
}

.cp-radar-dot-slate {
    background-color: #94A3B8;
}

@keyframes uiverse-ripple {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* ── Typography & Headings ── */
h1, h2, h3, h4, h5 {
    font-family: 'Outfit', sans-serif !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
}

h2 {
    font-size: 1.42rem !important;
    margin-top: 0.35rem !important;
    margin-bottom: 0.25rem !important;
}

h3 {
    font-size: 1.20rem !important;
    margin-top: 0.45rem !important;
    margin-bottom: 0.28rem !important;
}

h4 {
    font-size: 1.02rem !important;
    margin-top: 0.25rem !important;
    margin-bottom: 0.35rem !important;
}

/* ── Uiverse Cards & Symmetrical Form Containers ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.95) !important;
    border: 1px solid rgba(226, 232, 240, 0.90) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 
        0 2px 4px rgba(0, 0, 0, 0.02),
        0 8px 20px -3px rgba(15, 23, 42, 0.05),
        0 0 0 1px rgba(255, 255, 255, 0.8) inset !important;
    padding: 1.35rem 1.55rem !important;
    margin-bottom: 1.20rem !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    position: relative !important;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(99, 102, 241, 0.35) !important;
    box-shadow: 
        0 12px 28px -6px rgba(15, 23, 42, 0.09),
        0 0 0 1px rgba(99, 102, 241, 0.2) inset !important;
    transform: translateY(-2px) !important;
}

/* ── Uiverse Buttons Design System ── */

/* 1. Base Button Styling */
.stButton > button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border-radius: var(--radius-md) !important;
    padding: 0.58rem 1.30rem !important;
    border: 1.5px solid #CBD5E1 !important;
    background: #FFFFFF !important;
    color: var(--text-primary) !important;
    box-shadow: 0 2px 5px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.20s cubic-bezier(0.16, 1, 0.3, 1) !important;
    cursor: pointer !important;
}

.stButton > button:hover {
    border-color: #6366F1 !important;
    color: #4F46E5 !important;
    background: #F8FAFC !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(99, 102, 241, 0.15) !important;
}

.stButton > button:active {
    transform: translateY(1px) scale(0.985) !important;
}

/* 1b. Stepper Navigation Buttons */
button[key="nav_s1"],
button[key="nav_s2"],
button[key="nav_s3"],
button[key="nav_s4"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.90rem !important;
    letter-spacing: -0.01em !important;
    padding: 0.72rem 1.10rem !important;
    border-radius: var(--radius-md) !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04) !important;
}

button[key="nav_s1"]:hover,
button[key="nav_s2"]:hover,
button[key="nav_s3"]:hover,
button[key="nav_s4"]:hover {
    border-color: #6366F1 !important;
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 18px rgba(99, 102, 241, 0.18) !important;
}

/* 2. Primary Cosmic Glow Button */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 50%, #2563EB 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    color: #FFFFFF !important;
    box-shadow: 
        0 4px 14px rgba(79, 70, 229, 0.35),
        inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #4338CA 0%, #4F46E5 50%, #1D4ED8 100%) !important;
    border-color: rgba(255, 255, 255, 0.45) !important;
    color: #FFFFFF !important;
    transform: translateY(-2px) scale(1.015) !important;
    box-shadow: 
        0 8px 24px rgba(79, 70, 229, 0.48),
        inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
    filter: brightness(1.08) !important;
}

/* 3. Uiverse Vibrant Download Buttons */
.stDownloadButton > button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    border-radius: var(--radius-md) !important;
    padding: 0.60rem 1.35rem !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12) !important;
    transition: all 0.20s cubic-bezier(0.16, 1, 0.3, 1) !important;
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
}

/* Distinct color identity per export button */
button[key="dl_pdf_btn"],
div:has(> button[key="dl_pdf_btn"]) > button {
    background: linear-gradient(135deg, #E11D48 0%, #BE123C 100%) !important;
    box-shadow: 0 4px 14px rgba(225, 29, 72, 0.35) !important;
}
button[key="dl_pdf_btn"]:hover,
div:has(> button[key="dl_pdf_btn"]) > button:hover {
    background: linear-gradient(135deg, #BE123C 0%, #9F1239 100%) !important;
    box-shadow: 0 8px 22px rgba(225, 29, 72, 0.50) !important;
    transform: translateY(-2px) scale(1.015) !important;
}

button[key="dl_excel_btn"],
div:has(> button[key="dl_excel_btn"]) > button {
    background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
    box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35) !important;
}
button[key="dl_excel_btn"]:hover,
div:has(> button[key="dl_excel_btn"]) > button:hover {
    background: linear-gradient(135deg, #047857 0%, #065F46 100%) !important;
    box-shadow: 0 8px 22px rgba(5, 150, 105, 0.50) !important;
    transform: translateY(-2px) scale(1.015) !important;
}

button[key="dl_csv_btn"],
div:has(> button[key="dl_csv_btn"]) > button {
    background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
    box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35) !important;
}
button[key="dl_csv_btn"]:hover,
div:has(> button[key="dl_csv_btn"]) > button:hover {
    background: linear-gradient(135deg, #0369A1 0%, #075985 100%) !important;
    box-shadow: 0 8px 22px rgba(2, 132, 199, 0.50) !important;
    transform: translateY(-2px) scale(1.015) !important;
}

button[key="dl_json_btn"],
div:has(> button[key="dl_json_btn"]) > button {
    background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%) !important;
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35) !important;
}
button[key="dl_json_btn"]:hover,
div:has(> button[key="dl_json_btn"]) > button:hover {
    background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%) !important;
    box-shadow: 0 8px 22px rgba(124, 58, 237, 0.50) !important;
    transform: translateY(-2px) scale(1.015) !important;
}

.stDownloadButton > button:hover {
    transform: translateY(-2px) scale(1.015) !important;
    filter: brightness(1.08) !important;
}

/* ── Uiverse Metric / KPI Widgets ── */
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.95) !important;
    border: 1px solid rgba(226, 232, 240, 0.9) !important;
    border-top: 3.5px solid #4F46E5 !important;
    border-radius: var(--radius-md) !important;
    padding: 0.95rem 1.25rem !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
    transition: all 0.22s ease !important;
}

div[data-testid="stMetric"]:hover {
    border-color: rgba(99, 102, 241, 0.4) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.12) !important;
}

div[data-testid="stMetric"] label {
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.76rem !important;
    font-weight: 700 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.45rem !important;
    font-weight: 800 !important;
    color: var(--text-primary) !important;
}

/* ── Form Controls (Select, Input, Sliders) ── */
div[data-baseweb="select"] > div {
    border-radius: var(--radius-md) !important;
    border-color: var(--border-subtle) !important;
    background: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
}

div[data-baseweb="select"] > div:hover {
    border-color: var(--border-hover) !important;
}

div[data-baseweb="select"] > div:focus-within {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.20) !important;
}

input[type="text"], input[type="number"] {
    border-radius: var(--radius-md) !important;
    border-color: var(--border-subtle) !important;
    background: #FFFFFF !important;
}

input[type="text"]:focus, input[type="number"]:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.20) !important;
}

/* ── Uiverse Modern Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 2px solid var(--border-subtle) !important;
    padding-bottom: 0px !important;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.90rem !important;
    color: var(--text-muted) !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    padding: 0.60rem 1.25rem !important;
    border-bottom: 3px solid transparent !important;
    transition: all 0.20s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background: #F1F5F9 !important;
}

.stTabs [aria-selected="true"] {
    color: #4F46E5 !important;
    border-bottom-color: #4F46E5 !important;
    background: transparent !important;
    font-weight: 700 !important;
}

/* ── Dataframes ── */
.stDataFrame {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03) !important;
}

/* ── Uiverse Modern Timetable Grid ── */
.tt-grid-wrapper {
    overflow-x: auto;
    border-radius: var(--radius-lg);
    border: 1px solid rgba(226, 232, 240, 0.95);
    box-shadow: 
        0 4px 6px -1px rgba(0, 0, 0, 0.03),
        0 12px 24px -4px rgba(15, 23, 42, 0.06);
    background: #FFFFFF;
    margin: 1.0rem 0;
}

.tt-grid {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.82rem;
    table-layout: fixed;
    background: #FFFFFF;
}

/* Table Headers */
.tt-grid th {
    background: #0F172A;
    color: #FFFFFF;
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 0.80rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 12px 10px;
    text-align: center;
    border-bottom: 2px solid #1E293B;
}

.tt-grid th:first-child {
    border-top-left-radius: 12px;
}

.tt-grid th:last-child {
    border-top-right-radius: 12px;
}

.tt-grid td {
    padding: 8px 7px;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #E2E8F0;
    vertical-align: top;
    min-height: 82px;
    background: #FFFFFF;
    transition: background 0.15s ease;
}

.tt-grid td.day-header {
    background: #F1F5F9;
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 0.84rem;
    color: #1E293B;
    text-align: center;
    vertical-align: middle;
    border-right: 2px solid #CBD5E1;
    letter-spacing: -0.01em;
}

/* ── Uiverse Interactive Lesson Tile Card ── */
.tt-card {
    border-radius: var(--radius-sm);
    padding: 7px 9px;
    margin-bottom: 5px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    transition: all 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
    position: relative;
    cursor: default;
    border: 1px solid rgba(0, 0, 0, 0.06);
}

.tt-card:hover {
    box-shadow: 
        0 8px 20px -3px rgba(15, 23, 42, 0.14),
        0 0 0 1px rgba(99, 102, 241, 0.3) !important;
    transform: translateY(-3px) scale(1.02);
    z-index: 10;
}

.tt-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 4px;
    margin-bottom: 4px;
}

.tt-subject {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 0.86rem;
    letter-spacing: -0.01em;
}

.tt-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.tt-badge-lab {
    background: #D1FAE5;
    color: #065F46;
    border: 1px solid #A7F3D0;
}

.tt-badge-theory {
    background: #DBEAFE;
    color: #1E40AF;
    border: 1px solid #BFDBFE;
}

.tt-teacher {
    font-size: 0.74rem;
    font-weight: 600;
    color: #334155;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 3px;
}

.tt-room {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.70rem;
    color: #64748B;
    font-weight: 600;
}

.tt-pin {
    font-size: 0.72rem;
    margin-right: 3px;
}

/* Cell States (Lunch, Break, Conflicts) */
.tt-grid .lunch-cell {
    background: #F8FAFC !important;
    color: #64748B;
    font-size: 0.74rem;
    font-weight: 600;
    text-align: center;
    vertical-align: middle;
    letter-spacing: 0.04em;
    background-image: repeating-linear-gradient(45deg, #F8FAFC, #F8FAFC 10px, #F1F5F9 10px, #F1F5F9 20px) !important;
}

.tt-grid .break-cell {
    background: #F8FAFC !important;
    color: #64748B;
    font-size: 0.74rem;
    font-weight: 600;
    text-align: center;
    vertical-align: middle;
    background-image: repeating-linear-gradient(45deg, #F8FAFC, #F8FAFC 10px, #F1F5F9 10px, #F1F5F9 20px) !important;
}

.tt-grid .empty-cell {
    background: #FFFFFF;
}

.tt-grid .conflict-cell {
    border: 2px solid #DC2626 !important;
    background: #FEF2F2 !important;
}

.tt-conflict-tag {
    background: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FCA5A5;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 800;
    padding: 3px 6px;
    border-radius: 4px;
    display: inline-block;
    margin-top: 4px;
    letter-spacing: 0.04em;
    animation: uiverse-pulse-conflict 1.5s infinite;
}

@keyframes uiverse-pulse-conflict {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.tt-grid .highlight-slot {
    box-shadow: 0 0 0 3px #F59E0B inset !important;
    background: #FFFBEB !important;
}

/* ── Modern Legend Bar ── */
.tt-legend-bar {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 10px 18px;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: var(--radius-md);
    margin: 10px 0;
    font-size: 0.80rem;
    color: var(--text-secondary);
    flex-wrap: wrap;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.tt-legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.tt-legend-box {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid rgba(15, 23, 42, 0.12);
}

@media print {
    .cp-header, .stButton, .tt-legend-bar, section[data-testid="stSidebar"] { display: none !important; }
    .tt-grid th { background: #0F172A !important; -webkit-print-color-adjust: exact; color: #FFFFFF !important; }
    .tt-card { box-shadow: none !important; border: 1px solid #CBD5E1 !important; }
}
</style>
"""


def inject_css():
    """Inject Class Pilot Uiverse design system styles."""
    import streamlit as st
    st.markdown(CUSTOM_CSS.strip(), unsafe_allow_html=True)


def render_header(dataset=None, timetable=None, report=None):
    """Render top application header with Class Pilot high-tech branding and status indicators."""
    import streamlit as st

    if timetable and report:
        if report.hard_count == 0:
            status_html = '<span class="cp-status-pill cp-status-ready"><span class="cp-radar-dot cp-radar-dot-green"></span> Timetable Active &bull; 0 Conflicts</span>'
        else:
            status_html = f'<span class="cp-status-pill cp-status-alert"><span class="cp-radar-dot cp-radar-dot-red"></span> {report.hard_count} Conflicts</span>'
    elif dataset:
        cohorts = len(dataset.classes)
        teachers = len(dataset.teachers)
        status_html = f'<span class="cp-status-pill cp-status-ready"><span class="cp-radar-dot cp-radar-dot-green"></span> Model Loaded &bull; {cohorts} Classes, {teachers} Faculty</span>'
    else:
        status_html = '<span class="cp-status-pill cp-status-neutral"><span class="cp-radar-dot cp-radar-dot-slate"></span> Engine Ready &bull; Standby</span>'

    header_html = (
        '<div class="cp-header">'
        '<div class="cp-brand-group">'
        '<div class="cp-logo-badge">'
        '<svg width="26" height="26" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<defs>'
        '<linearGradient id="cpIconGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#FFFFFF"/>'
        '<stop offset="100%" stop-color="#E0E7FF"/>'
        '</linearGradient>'
        '</defs>'
        '<path d="M16 4L26 25L16 20L6 25L16 4Z" fill="url(#cpIconGrad)"/>'
        '<circle cx="16" cy="14" r="2.4" fill="#38BDF8"/>'
        '</svg>'
        '</div>'
        '<div class="cp-brand-text">'
        '<div class="cp-brand-title">'
        'Class Pilot'
        '<span class="cp-brand-badge">AI TIMETABLE ENGINE</span>'
        '</div>'
        '<span class="cp-brand-subtitle">Automated Institutional Schedule Optimizer</span>'
        '</div>'
        '</div>'
        f'<div class="cp-header-status">{status_html}</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def render_legend_html() -> str:
    """Render a clean legend explaining timetable colors and symbols."""
    return (
        '<div class="tt-legend-bar">'
        '<span style="font-family: \'Outfit\', sans-serif; font-weight: 700; color: #0F172A;">Legend:</span>'
        '<div class="tt-legend-item">'
        '<div class="tt-legend-box" style="background: #EFF6FF; border-left: 4px solid #3B82F6;"></div>'
        '<span style="font-weight: 600;">Theory Lecture</span>'
        '</div>'
        '<div class="tt-legend-item">'
        '<div class="tt-legend-box" style="background: #ECFDF5; border-left: 4px solid #10B981;"></div>'
        '<span style="font-weight: 600;">Laboratory Block</span>'
        '</div>'
        '<div class="tt-legend-item">'
        '<div class="tt-legend-box" style="background: #F8FAFC; border: 1.5px dashed #CBD5E1;"></div>'
        '<span style="font-weight: 600;">Lunch / Recess</span>'
        '</div>'
        '<div class="tt-legend-item">'
        '<div class="tt-legend-box" style="background: #FEF2F2; border: 1.5px solid #DC2626;"></div>'
        '<span style="font-weight: 600;">Constraint Conflict</span>'
        '</div>'
        '</div>'
    )


def render_timetable_html(
    timetable, dataset, view_type: str, filter_value: str,
    conflicts: set | None = None,
    highlight_text: str = "",
) -> str:
    """Render single timetable view (Class, Teacher, Room) with Theory vs Lab colors and clear legends."""
    ts = dataset.time_structure
    days = ts.day_names
    periods = list(range(ts.periods_per_day))

    from collections import defaultdict
    grid = defaultdict(lambda: defaultdict(list))

    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, room_name = value

        show = False
        if view_type == "class" and session.class_name == filter_value:
            show = True
        elif view_type == "teacher" and session.teacher_name == filter_value:
            show = True
        elif view_type == "room" and room_name == filter_value:
            show = True

        if show:
            subj = dataset.subjects.get(session.subject_code)
            is_lab = bool(subj and subj.subject_type == "lab")

            for p_off in range(session.block_size):
                p = period + p_off
                if p < ts.periods_per_day:
                    grid[day][p].append({
                        "subject": session.subject_code,
                        "teacher": session.teacher_name if view_type != "teacher" else session.class_name,
                        "room": room_name if view_type != "room" else session.teacher_name,
                        "is_lab": is_lab,
                        "class_name": session.class_name,
                    })

    lunch_slot = -1
    if view_type == "class" and filter_value in dataset.classes:
        lunch_slot = dataset.classes[filter_value].lunch_break_slot

    if conflicts is None:
        conflicts = set()

    h_term = highlight_text.strip().lower()

    # Legend + Table Wrapper
    html = render_legend_html()
    html += '<div class="tt-grid-wrapper"><table class="tt-grid">'

    # Header row
    html += "<tr><th style='width:115px;'>Day</th>"
    for p in periods:
        label = f"Period {p+1}"
        if p in ts.break_periods:
            label = "Recess"
        html += f"<th>{label}</th>"
    html += "</tr>"

    # Data rows
    for d_idx, day_name in enumerate(days):
        html += f'<tr><td class="day-header">{day_name}</td>'
        for p in periods:
            is_lunch = (p == lunch_slot)
            is_break = (p in ts.break_periods)
            is_conflict = (d_idx, p) in conflicts
            entries = grid[d_idx][p]

            is_highlighted = False
            if h_term and entries:
                for e in entries:
                    if (h_term in e["subject"].lower() or
                            h_term in e["teacher"].lower() or
                            h_term in e["room"].lower() or
                            h_term in e["class_name"].lower()):
                        is_highlighted = True
                        break

            css_class = ""
            if is_conflict:
                css_class = "conflict-cell"
            elif is_highlighted:
                css_class = "highlight-slot"
            elif is_lunch:
                css_class = "lunch-cell"
            elif is_break:
                css_class = "break-cell"
            elif not entries:
                css_class = "empty-cell"

            html += f'<td class="{css_class}">'

            if is_lunch and not entries:
                html += '<span style="color:#64748B; font-weight:700;">🍴 Lunch Break</span>'
            elif is_break and not entries:
                html += '<span style="color:#64748B; font-weight:700;">☕ Recess</span>'
            elif entries:
                for e in entries:
                    is_lab = e["is_lab"]
                    theme = LAB_THEME if is_lab else get_subject_theme(e["subject"], is_lab=False)
                    badge_class = "tt-badge-lab" if is_lab else "tt-badge-theory"
                    badge_label = "LAB" if is_lab else "THEORY"

                    html += f'<div class="tt-card" style="border-left: 4px solid {theme["border"]}; background: {theme["bg"]};">'
                    html += '<div class="tt-card-top">'
                    html += f'<span class="tt-subject" style="color: {theme["text"]};">{e["subject"]}</span>'
                    html += f'<span class="tt-badge {badge_class}">{badge_label}</span>'
                    html += '</div>'
                    html += f'<div class="tt-teacher">{e["teacher"]}</div>'
                    html += f'<div class="tt-room"><span class="tt-pin">📍</span>{e["room"]}</div>'
                    html += '</div>'

                if is_conflict:
                    html += '<div class="tt-conflict-tag">⚠ CONFLICT</div>'

            html += "</td>"
        html += "</tr>"

    html += "</table></div>"
    return html


def render_master_timetable_html(
    timetable, dataset, group_by: str = "class", highlight_text: str = ""
) -> str:
    """Render Master Schedule grid grouped by Class or Room."""
    ts = dataset.time_structure
    entities = list(dataset.classes.keys()) if group_by == "class" else list(dataset.rooms.keys())
    h_term = highlight_text.strip().lower()

    from collections import defaultdict
    slot_map = defaultdict(list)

    for session, val in timetable.assignment.items():
        if val is None:
            continue
        day, period, room = val
        for p_off in range(session.block_size):
            p = period + p_off
            ent = session.class_name if group_by == "class" else room
            slot_map[(day, p, ent)].append({
                "subject": session.subject_code,
                "teacher": session.teacher_name,
                "room": room,
                "class_name": session.class_name,
                "is_lab": bool(dataset.subjects.get(session.subject_code, None) and dataset.subjects[session.subject_code].subject_type == "lab"),
            })

    html = render_legend_html()
    html += '<div class="tt-grid-wrapper" style="max-height: 720px;"><table class="tt-grid">'

    # Header row
    html += '<tr><th style="width:125px;position:sticky;left:0;z-index:11;">Day &amp; Slot</th>'
    for ent in entities:
        html += f'<th>{ent}</th>'
    html += '</tr>'

    for day_idx, day_name in enumerate(ts.day_names):
        for p in range(ts.periods_per_day):
            slot_name = f"{day_name} P{p+1}"
            html += f'<tr><td class="day-header" style="position:sticky;left:0;z-index:10;">{slot_name}</td>'

            for ent in entities:
                entries = slot_map.get((day_idx, p, ent), [])
                is_highlighted = False
                if h_term and entries:
                    for e in entries:
                        if (h_term in e["subject"].lower() or
                                h_term in e["teacher"].lower() or
                                h_term in e["room"].lower() or
                                h_term in e["class_name"].lower()):
                            is_highlighted = True
                            break

                css = "highlight-slot" if is_highlighted else ("empty-cell" if not entries else "")
                html += f'<td class="{css}">'

                if entries:
                    for e in entries:
                        is_lab = e["is_lab"]
                        theme = LAB_THEME if is_lab else get_subject_theme(e["subject"], is_lab=False)
                        badge_label = "LAB" if is_lab else "THEORY"
                        badge_class = "tt-badge-lab" if is_lab else "tt-badge-theory"
                        label = f"{e['teacher']} [{e['room']}]" if group_by == "class" else f"{e['class_name']} ({e['teacher']})"

                        html += f'<div class="tt-card" style="border-left: 3.5px solid {theme["border"]}; background: {theme["bg"]}; padding: 6px 8px; margin: 2px 0;">'
                        html += '<div class="tt-card-top">'
                        html += f'<span class="tt-subject" style="color: {theme["text"]}; font-size: 0.80rem;">{e["subject"]}</span>'
                        html += f'<span class="tt-badge {badge_class}" style="font-size: 0.58rem;">{badge_label}</span>'
                        html += '</div>'
                        html += f'<div class="tt-teacher" style="font-size: 0.70rem;">{label}</div>'
                        html += '</div>'

                html += '</td>'
            html += '</tr>'

    html += '</table></div>'
    return html
