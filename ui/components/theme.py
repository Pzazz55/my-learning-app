"""UI theme and styling components.

Two appearance modes are supported. Each mode is a complete, self-contained
set of colours chosen so text/background pairs meet WCAG AA contrast:

* Light mode uses dark slate text (#0f2a43) on light surfaces (#ffffff /
  gradient) and a deep coral primary button (#c2410c) with white text.
* Dark mode uses light text (#eef3fb) on dark slate surfaces (#101a2e /
  #1b2942) and a warm amber primary button (#ffd166) with dark text.

Both ``inject_styles`` (student workspace) and ``inject_parent_theme`` (parent
pages) inject the light baseline plus, when Dark is selected, a dark override
block that re-colours Streamlit's own widgets (selects, dropdown menus,
expanders, sidebar, dataframes) so nothing falls back to a mismatched colour.
"""

from __future__ import annotations

import streamlit as st

_FONTS = "@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');"

# ---------------------------------------------------------------------------
# Student workspace theme
# ---------------------------------------------------------------------------


def inject_styles(theme: str = "Light") -> None:
    """Inject the student-workspace CSS for the requested theme."""
    dark = _workspace_dark() if theme == "Dark" else ""
    css = (
        "<style>"
        + _FONTS
        + """
        :root { --ink:#0f2a43; --muted:#47566b; --line:#d6e5eb; --sky:#bde8ff; --sun:#e6a700; }
        html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); font-size:1.04rem; }
        .stApp { background:linear-gradient(120deg, #fff4cf 0%, #dff3ff 48%, #e4f8eb 100%); }
        h1, h2, h3 { font-family:'Space Grotesk', sans-serif !important; letter-spacing:0 !important; color:var(--ink) !important; }
        .block-container { max-width:1100px; padding:3.2rem 2rem 4rem; }
        .brand { display:flex; justify-content:space-between; align-items:center; margin-bottom:3.5rem; }
        .brand-mark { font-family:'Space Grotesk'; font-weight:700; font-size:1.4rem; letter-spacing:0; color:var(--ink); }
        .brand-mark span { color:#c2410c; }
        .eyebrow { color:#b3350f; font-size:.88rem; font-weight:700; text-transform:uppercase; letter-spacing:.12em; }
        .hero h1 { font-size:clamp(3rem, 7vw, 5.5rem); line-height:.98; max-width:720px; margin:.55rem 0 1.1rem; color:var(--ink); }
        .hero p { color:var(--muted); font-size:1.2rem; max-width:600px; line-height:1.6; }
        .pill { border:2px solid #79bfdc; background:#fff; border-radius:30px; padding:.6rem .9rem; color:var(--ink); font-size:.95rem; font-weight:600; }
        .question-panel, .result-panel { background:#fff; border:2px solid #b7d4df; border-radius:12px; padding:1.5rem; box-shadow:0 18px 50px rgba(35,68,91,.12); }
        .stButton > button, .stFormSubmitButton > button { border-radius:12px; border:0; background:#c2410c; color:#ffffff; font-size:1.05rem; font-weight:700; min-height:3.2rem; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#9a3412; color:#ffffff; }
        div[data-testid="stMetric"] { background:#fff; border:2px solid var(--sun); border-radius:12px; padding:1.15rem; }
        div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        div[data-testid="stMetricLabel"] { font-size:1rem; }
        div[data-testid="stMetricValue"] { font-size:1.8rem; }
        .timer { font-family:'Space Grotesk'; font-size:2.8rem; font-weight:700; color:#b3350f; text-align:right; }
        .timer-label { color:var(--muted); font-size:.95rem; text-align:right; }
        .clock { text-align:right; margin-bottom:.4rem; }
        .clock-time { font-family:'Space Grotesk'; font-size:1.6rem; font-weight:700; color:var(--ink); line-height:1.1; }
        .clock-zone { color:var(--muted); font-size:.82rem; font-weight:700; letter-spacing:.06em; }
        .clock-date { color:var(--muted); font-size:.78rem; }
        .question-index { color:#b3350f; font-size:.95rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em; }
        .question-text { font-family:'Space Grotesk'; font-size:clamp(1.6rem, 3.4vw, 2.35rem); line-height:1.2; margin:.65rem 0 1.8rem; }
        .stRadio > div { gap:.55rem; }
        .stRadio label, .stRadio label p { color:var(--ink) !important; }
        .stRadio label { background:#fff; border:2px solid #79bfdc; border-radius:12px; padding:.9rem 1rem; font-size:1.08rem; }
        .stRadio label:hover { border-color:#c2410c; background:#fff4d1; }
        .stSelectbox label, .stTextInput label, .stNumberInput label { font-size:1.05rem !important; font-weight:700; color:var(--ink) !important; }
        .stSelectbox [data-baseweb="select"], .stTextInput input, .stNumberInput input { background:#fff; border:2px solid #79bfdc; color:var(--ink); font-size:1.05rem; }
        .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; opacity:1 !important; }
        .stSelectbox [data-baseweb="select"] svg { opacity:0 !important; }
        .stSelectbox [data-baseweb="select"] { position:relative; padding-right:2.2rem; }
        .stSelectbox [data-baseweb="select"]::after { content:"\\25BE"; position:absolute; right:.75rem; top:50%; transform:translateY(-50%); color:var(--ink); font-size:1.1rem; font-weight:700; line-height:1; pointer-events:none; }
        .stTextInput input::placeholder, .stNumberInput input::placeholder { color:#8aa0af; opacity:1; }
        div[role="listbox"], div[role="option"], [data-baseweb="popover"], [data-baseweb="menu"] { background:#fff !important; color:var(--ink) !important; }
        div[role="option"] *, [data-baseweb="menu"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        div[role="option"]:hover, [data-baseweb="menu"] li:hover { background:#eef8ff !important; }
        section[data-testid="stSidebar"] { background:#eef6fb !important; }
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] * { color:var(--ink) !important; }
        /* Sidebar widget labels and values ("LLM model", "Temperature", …) */
        section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] label * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; font-weight:600; }
        section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"], section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"], section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"] { color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] { background:#fff !important; border:2px solid #79bfdc; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] [data-baseweb="popover"], section[data-testid="stSidebar"] [role="option"] { background:#fff !important; color:var(--ink) !important; }
        section[data-testid="stSidebar"] [role="option"] * { color:var(--ink) !important; }
        /* Appearance toggle: keep its two options readable on every screen. */
        section[data-testid="stSidebar"] .stRadio label { background:#fff !important; border:2px solid #79bfdc !important; color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stRadio label p { color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stRadio label:hover { border-color:#c2410c !important; background:#fff4d1 !important; }
        div[data-testid="stExpander"] { background:#fff; border:2px solid #b7d4df !important; border-radius:12px; }
        div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { color:var(--ink) !important; }
        div[data-testid="stExpander"] svg { fill:var(--ink) !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-color:#b7d4df !important; }
        [data-testid="stAlert"] { color:var(--ink) !important; }
        [data-testid="stAlert"] p { color:var(--ink) !important; }
        .success-box { background:#fff0b8; border:2px solid #f3bd35; color:#0f2a43; padding:1.3rem 1.5rem; border-radius:14px; font-size:1.15rem; }
        .celebration { color:#b3350f; font-family:'Space Grotesk'; font-size:1.3rem; font-weight:700; text-align:center; margin:.7rem 0 1.3rem; }
        .footer-note { color:var(--muted); font-size:.9rem; text-align:center; margin-top:3rem; }
        """
        + dark
        + "</style>"
    )
    st.markdown(css, unsafe_allow_html=True)


def _workspace_dark() -> str:
    return """
        :root { --ink:#eef3fb; --muted:#b8c4d9; --paper:#101a2e; --card:#1b2942; --line:#3a4d6d; --sky:#7cc4f0; --sun:#ffd166; }
        .stApp { background:linear-gradient(120deg, #0f1a2e 0%, #16233c 48%, #12262f 100%); }
        h1, h2, h3 { color:var(--ink) !important; }
        .hero h1, .brand, .brand-mark, .question-text { color:var(--ink) !important; }
        .hero p { color:var(--muted); }
        .eyebrow, .question-index, .timer, .celebration { color:#ffb08a !important; }
        .stMarkdown, .stMarkdown p, .stCaption, label, label p, .stRadio label, .stRadio label p { color:var(--ink) !important; }
        .pill { background:#1b2942; border-color:#7cc4f0; color:var(--ink); }
        .question-panel, .result-panel { background:#1b2942; border-color:#3a4d6d; box-shadow:0 18px 50px rgba(0,0,0,.32); }
        div[data-testid="stForm"] { background:#1b2942; border:2px solid #7cc4f0; border-radius:14px; padding:1.25rem; }
        .stButton > button, .stFormSubmitButton > button { background:#ffd166; color:#101a2e; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#ffb703; color:#101a2e; }
        div[data-testid="stMetric"] { background:#1b2942; border-color:#ffd166; }
        div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        .clock-time { color:var(--ink) !important; }
        .clock-zone, .clock-date { color:var(--muted) !important; }
        .stRadio label { background:#1b2942; border-color:#3a4d6d; color:var(--ink); }
        .stRadio label:hover { border-color:#ffd166; background:#243453; }
        .stSelectbox label, .stTextInput label, .stNumberInput label { color:var(--ink) !important; }
        .stSelectbox [data-baseweb="select"], .stTextInput input, .stNumberInput input { background:#1b2942; color:var(--ink); border-color:#7cc4f0; }
        .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; opacity:1 !important; }
        .stSelectbox [data-baseweb="select"] input, .stSelectbox [data-baseweb="select"] div { background:#1b2942 !important; }
        .stTextInput input::placeholder, .stNumberInput input::placeholder { color:#8ba0b8; opacity:1; }
        div[role="listbox"], ul[role="listbox"], div[role="option"], li[role="option"], [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] ul { background:#1b2942 !important; color:var(--ink) !important; }
        div[role="option"], li[role="option"], [data-baseweb="menu"] li { background:#1b2942 !important; color:var(--ink) !important; }
        div[role="option"] *, li[role="option"] *, [data-baseweb="menu"] li * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        div[role="option"]:hover, li[role="option"]:hover, div[role="option"][aria-selected="true"], li[role="option"][aria-selected="true"], [data-baseweb="menu"] li:hover { background:#243453 !important; }
        [data-testid="stAlert"] { color:var(--ink) !important; }
        [data-testid="stAlert"] p { color:var(--ink) !important; }
        .success-box { background:#3a3416; border-color:#ffd166; color:#fdf6d8; }
        section[data-testid="stSidebar"] { background:#101a2e !important; }
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] * { color:var(--ink) !important; }
        /* Sidebar widget labels and values ("LLM model", "Temperature", …) */
        section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] label * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; font-weight:600; }
        section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"], section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"], section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"] { color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] { background:#1b2942 !important; border:2px solid #7cc4f0; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] [data-baseweb="popover"], section[data-testid="stSidebar"] [role="option"] { background:#1b2942 !important; color:var(--ink) !important; }
        section[data-testid="stSidebar"] [role="option"] * { color:var(--ink) !important; }
        /* Appearance toggle: keep its two options readable on every screen. */
        section[data-testid="stSidebar"] .stRadio label { background:#1b2942 !important; border:2px solid #3a4d6d !important; color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stRadio label p { color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stRadio label:hover { border-color:#ffd166 !important; background:#243453 !important; }
        div[data-testid="stExpander"] { background:#1b2942; border-color:#3a4d6d !important; }
        div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { color:var(--ink) !important; }
        div[data-testid="stExpander"] svg { fill:var(--ink) !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] { background:#1b2942; border-color:#3a4d6d !important; }
    """


# ---------------------------------------------------------------------------
# Parent pages theme
# ---------------------------------------------------------------------------


def inject_parent_theme(theme: str = "Dark") -> None:
    """Inject the parent-page CSS for the requested theme."""
    dark = _parent_dark() if theme == "Dark" else ""
    css = (
        "<style>"
        + _FONTS
        + """
        :root { --ink:#0f2a43; --muted:#47566b; --line:#d6e5eb; --sky:#bde8ff; --sun:#e6a700; }
        html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); font-size:1.04rem; }
        .stApp { background:linear-gradient(120deg,#fff4cf 0%,#dff3ff 48%,#e4f8eb 100%); }
        h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:var(--ink) !important; }
        .block-container { max-width:1150px; padding:3rem 2rem; }
        .panel { background:#fff; border:2px solid #b7d4df; border-radius:12px; padding:1.25rem; }
        .brand { font-family:'Space Grotesk'; font-weight:700; font-size:1.4rem; margin-bottom:3rem; color:var(--ink); }
        .brand span { color:#c2410c; }
        label, label p, .stCaption { color:var(--ink) !important; font-weight:600; }
        .stMarkdown, .stMarkdown p { color:var(--ink); }
        .stButton > button, .stFormSubmitButton > button { border-radius:12px; background:#c2410c; color:#fff; font-size:1.05rem; min-height:3rem; border:0; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#9a3412; color:#fff; }
        div[data-testid="stMetric"] { background:#fff; border:2px solid var(--sun); border-radius:12px; padding:1rem; }
        div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] { background:#fff; border:2px solid #79bfdc; color:var(--ink); }
        .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; opacity:1 !important; }
        .stSelectbox [data-baseweb="select"] svg { opacity:0 !important; }
        .stSelectbox [data-baseweb="select"] { position:relative; padding-right:2.2rem; }
        .stSelectbox [data-baseweb="select"]::after { content:"\\25BE"; position:absolute; right:.75rem; top:50%; transform:translateY(-50%); color:var(--ink); font-size:1.1rem; font-weight:700; line-height:1; pointer-events:none; }
        .stTextInput input::placeholder, .stNumberInput input::placeholder { color:#8aa0af; opacity:1; }
        div[role="listbox"], div[role="option"], [data-baseweb="popover"], [data-baseweb="menu"] { background:#fff !important; color:var(--ink) !important; }
        div[role="option"] *, [data-baseweb="menu"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        div[role="option"]:hover, [data-baseweb="menu"] li:hover { background:#eef8ff !important; }
        div[data-testid="stExpander"] { background:#fff; border:2px solid #b7d4df !important; border-radius:12px; }
        div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { color:var(--ink) !important; }
        div[data-testid="stExpander"] svg { fill:var(--ink) !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-color:#b7d4df !important; }
        div[data-testid="stAlert"] { color:var(--ink) !important; }
        div[data-testid="stAlert"] p { color:var(--ink) !important; }
        .results-table { width:100%; border-collapse:collapse; color:var(--ink); background:#fff; font-size:.9rem; }
        .results-table th { background:#dff3ff; color:var(--ink); text-align:left; }
        .results-table th, .results-table td { border:1px solid #b7d4df; padding:.65rem; vertical-align:top; }
        section[data-testid="stSidebar"] { background:#eef6fb !important; }
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] * { color:var(--ink) !important; }
        section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] label * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; font-weight:600; }
        section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"], section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"], section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"] { color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] { background:#fff !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] [data-baseweb="popover"], section[data-testid="stSidebar"] [role="option"] { background:#fff !important; color:var(--ink) !important; }
        section[data-testid="stSidebar"] [role="option"] * { color:var(--ink) !important; }
        """
        + dark
        + "</style>"
    )
    st.markdown(css, unsafe_allow_html=True)


def _parent_dark() -> str:
    return """
        :root { --ink:#eef3fb; --muted:#b8c4d9; --line:#3a4d6d; --sky:#7cc4f0; --sun:#ffd166; }
        .stApp { background:linear-gradient(120deg,#0f1a2e 0%,#16233c 48%,#12262f 100%); }
        h1,h2,h3, .brand, .stMarkdown, .stMarkdown p, label, label p, .stCaption { color:var(--ink) !important; }
        .panel, div[data-testid="stExpander"] { background:#1b2942; border-color:#3a4d6d; }
        div[data-testid="stForm"] { background:#1b2942; border:2px solid #7cc4f0; border-radius:14px; padding:1.25rem; }
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"], .stDataFrame { background:#1b2942; color:var(--ink); border-color:#7cc4f0; }
        .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; opacity:1 !important; }
        .stSelectbox [data-baseweb="select"] input, .stSelectbox [data-baseweb="select"] div { background:#1b2942 !important; }
        .stTextInput input::placeholder, .stNumberInput input::placeholder { color:#8ba0b8; opacity:1; }
        div[role="listbox"], ul[role="listbox"], div[role="option"], li[role="option"], [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] ul { background:#1b2942 !important; color:var(--ink) !important; }
        div[role="option"], li[role="option"], [data-baseweb="menu"] li { background:#1b2942 !important; color:var(--ink) !important; }
        div[role="option"] *, li[role="option"] *, [data-baseweb="menu"] li * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        div[role="option"]:hover, li[role="option"]:hover, div[role="option"][aria-selected="true"], li[role="option"][aria-selected="true"], [data-baseweb="menu"] li:hover { background:#243453 !important; }
        [data-testid="stAlert"] { color:var(--ink) !important; }
        [data-testid="stAlert"] p { color:var(--ink) !important; }
        section[data-testid="stSidebar"] { background:#101a2e !important; }
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] * { color:var(--ink) !important; }
        section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] label * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; font-weight:600; }
        section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"], section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"], section[data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"] { color:var(--ink) !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] { background:#1b2942 !important; border:2px solid #7cc4f0; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        section[data-testid="stSidebar"] [data-baseweb="popover"], section[data-testid="stSidebar"] [role="option"] { background:#1b2942 !important; color:var(--ink) !important; }
        section[data-testid="stSidebar"] [role="option"] * { color:var(--ink) !important; }
        .stButton > button, .stFormSubmitButton > button { background:#ffd166; color:#101a2e; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#ffb703; color:#101a2e; }
        div[data-testid="stMetric"] { background:#1b2942; border-color:#ffd166; }
        div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
        div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { color:var(--ink) !important; }
        .results-table { width:100%; border-collapse:collapse; color:var(--ink); background:#1b2942; font-size:.9rem; }
        .results-table th { background:#2b3d5c; color:#ffffff; text-align:left; }
        .results-table th, .results-table td { border:1px solid #3a4d6d; padding:.65rem; vertical-align:top; }
    """