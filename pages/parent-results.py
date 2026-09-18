from __future__ import annotations

import json
import hmac
from html import escape
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
from llm_backend import load_config, load_grades, load_topics, read_setting

DB_PATH = Path(__file__).parent.parent / "education_app.db"
load_dotenv(DB_PATH.parent / ".env")
SUBJECT_CATALOG = list(load_topics()["subjects"])
CONFIG = load_config()


def format_question_time(seconds: float) -> str:
    total_seconds = max(0, round(float(seconds or 0)))
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes}m {remaining:02d}s" if minutes else f"{remaining}s"


def format_exam_duration(start_time: str, end_time: str) -> str:
    try:
        seconds = (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds()
    except (TypeError, ValueError):
        return "Unavailable"
    return format_question_time(seconds)


def format_local_time(value: str) -> str:
    """Render a stored UTC timestamp in the timezone configured in config.json."""
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return "Unavailable"
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(CONFIG["zone"]).strftime("%d %b %Y, %H:%M %Z")


def format_options(options: list[str] | None) -> str:
    """List a question's answer options one per line so parents can review them."""
    if not options:
        return "—"
    return "<br>".join(f"{letter}) {escape(str(option))}" for letter, option in zip("ABCDEFGH", options))

st.set_page_config(page_title="Parent Results · Study Sprint", page_icon="▦", layout="wide")
theme = st.sidebar.radio("Appearance", ["Light", "Dark"], index=1, horizontal=True, key="appearance")
dark_theme = """
    :root { --ink:#f6f7ff; --muted:#c2cbe0; --line:#455473; --sky:#5bbce8; --sun:#f6c94c; }
    .stApp { background:linear-gradient(120deg,#17223a 0%,#24334e 48%,#193b42 100%); }
    h1, h2, h3, .brand, .stMarkdown, .stMarkdown p, label, label p, .stCaption { color:#f6f7ff !important; }
    .panel, div[data-testid="stExpander"] { background:#222e49; border-color:#455473; }
    div[data-testid="stForm"] { background:#222e49; border:2px solid #5bbce8; border-radius:14px; padding:1.25rem; }
    .stTextInput input, .stSelectbox [data-baseweb="select"], .stDataFrame { background:#263653; color:#f6f7ff; border-color:#5bbce8; }
    .stSelectbox [data-baseweb="select"] * { color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; opacity:1 !important; }
    .stSelectbox [data-baseweb="select"] svg { opacity:0 !important; }
    .stSelectbox [data-baseweb="select"] { position:relative; padding-right:2.2rem; }
    .stSelectbox [data-baseweb="select"]::after { content:"▾"; position:absolute; right:.75rem; top:50%; transform:translateY(-50%); color:#bde8ff; font-size:1.1rem; font-weight:700; line-height:1; pointer-events:none; }
    .stTextInput input::placeholder { color:#c2cbe0; opacity:1; }
    div[role="listbox"], div[role="option"], [data-baseweb="popover"] { background:#263653; color:#f6f7ff; }
    div[role="option"] * { color:#f6f7ff !important; }
    [data-testid="stAlert"] { color:#f6f7ff; }
    section[data-testid="stSidebar"], section[data-testid="stSidebar"] * { color:#f6f7ff !important; }
    section[data-testid="stSidebar"] .stSelectbox .react-aria-ComboBox > div { background:#263653 !important; border:2px solid #5bbce8 !important; border-radius:10px; }
    section[data-testid="stSidebar"] .stSelectbox input[role="combobox"] { background:#263653 !important; color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; }
    section[data-testid="stSidebar"] .stSelectbox button[aria-label="Open"] { background:#314563 !important; color:#bde8ff !important; }
    section[data-testid="stSidebar"] .stSelectbox button[aria-label="Open"] svg { color:#bde8ff !important; fill:#bde8ff !important; stroke:#bde8ff !important; }
    .stButton > button, .stFormSubmitButton > button { background:#f6c94c; color:#17223a; }
    .stButton > button:hover, .stFormSubmitButton > button:hover { background:#ff927d; color:#17223a; }
    div[data-testid="stMetric"] { background:#263653; border-color:#f6c94c; }
    div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; }
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { color:#f6f7ff !important; }
    .results-table { width:100%; border-collapse:collapse; color:#f6f7ff; background:#263653; font-size:.9rem; }
    .results-table th { background:#39516f; color:#fff; text-align:left; }
    .results-table th, .results-table td { border:1px solid #5b7190; padding:.65rem; vertical-align:top; }
    .stSidebar { background:#17223a; }
""" if theme == "Dark" else ""
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#17324d; --muted:#526879; --line:#d6e5eb; --sky:#bde8ff; --sun:#ffd86b; }
    html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); font-size:1.04rem; }
    .stApp { background:linear-gradient(120deg,#fff4cf 0%,#dff3ff 48%,#e4f8eb 100%); }
    h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:var(--ink) !important; }
    .block-container { max-width:1150px; padding:3rem 2rem; }
    .panel { background:#fff; border:2px solid #b7d4df; border-radius:12px; padding:1.25rem; }
    .brand { font-family:'Space Grotesk'; font-weight:700; font-size:1.4rem; margin-bottom:3rem; color:var(--ink); }
    .brand span { color:#f06f5d; }
    label, label p, .stCaption { color:var(--ink) !important; font-weight:600; }
    .stButton > button, .stFormSubmitButton > button { border-radius:12px; background:#ef705c; color:white; font-size:1.05rem; min-height:3rem; }
    .stButton > button:hover, .stFormSubmitButton > button:hover { background:#ef705c; color:white; }
    div[data-testid="stMetric"] { background:#fff; border:2px solid var(--sun); border-radius:12px; padding:1rem; }
    .stTextInput input, .stSelectbox [data-baseweb="select"] { background:#fff; border:2px solid #79bfdc; color:var(--ink); }
    .stSelectbox [data-baseweb="select"] * { color:#17324d !important; -webkit-text-fill-color:#17324d !important; opacity:1 !important; }
    .stSelectbox [data-baseweb="select"] svg { opacity:0 !important; }
    .stSelectbox [data-baseweb="select"] { position:relative; padding-right:2.2rem; }
    .stSelectbox [data-baseweb="select"]::after { content:"▾"; position:absolute; right:.75rem; top:50%; transform:translateY(-50%); color:#17324d; font-size:1.1rem; font-weight:700; line-height:1; pointer-events:none; }
    .results-table { width:100%; border-collapse:collapse; color:#17324d; background:#fff; font-size:.9rem; }
    .results-table th { background:#dff3ff; color:#17324d; text-align:left; }
    .results-table th, .results-table td { border:1px solid #b7d4df; padding:.65rem; vertical-align:top; }
    """ + dark_theme + "</style>",
    unsafe_allow_html=True,
)

st.markdown('<div class="brand">study<span>·</span>sprint / parent view</div>', unsafe_allow_html=True)

expected_username = read_setting("PARENT_USERNAME")
expected_password = read_setting("PARENT_PASSWORD")

if not expected_username or not expected_password:
    st.error("Parent credentials are not configured. Set PARENT_USERNAME and PARENT_PASSWORD in .streamlit/secrets.toml, Streamlit Cloud secrets, or .env.")
    st.stop()

if not st.session_state.get("parent_authenticated", False):
    st.markdown("## Parent sign in")
    st.caption("Sign in to review or manage saved exam results.")
    with st.form("parent_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        valid_username = hmac.compare_digest(username, expected_username)
        valid_password = hmac.compare_digest(password, expected_password)
        if valid_username and valid_password:
            st.session_state.parent_authenticated = True
            st.rerun()
        st.error("Incorrect username or password.")
    st.stop()

header_left, header_right = st.columns([4, 1])
header_left.markdown("## Results library")
header_left.caption("Review completed exams saved on this device.")
if header_right.button("Sign out"):
    st.session_state.parent_authenticated = False
    st.rerun()

if not DB_PATH.exists():
    st.info("No exam results yet. Completed exams will appear here.")
    st.stop()

connection = sqlite3.connect(DB_PATH)
connection.row_factory = sqlite3.Row
columns = {row["name"] for row in connection.execute("PRAGMA table_info(exams)")}
if not columns:
    # The database file exists but no exam has ever been stored yet.
    connection.close()
    st.info("No exam results yet. Completed exams will appear here.")
    st.stop()
if "school_district" not in columns:
    connection.execute("ALTER TABLE exams ADD COLUMN school_district TEXT NOT NULL DEFAULT ''")
if "school_state" not in columns:
    connection.execute("ALTER TABLE exams ADD COLUMN school_state TEXT NOT NULL DEFAULT ''")
if "topic" not in columns:
    connection.execute("ALTER TABLE exams ADD COLUMN topic TEXT NOT NULL DEFAULT ''")
connection.commit()
rows = connection.execute("SELECT * FROM exams ORDER BY end_time DESC").fetchall()
connection.close()

with st.container(border=True):
    st.markdown("#### Filter results")
    first, second, third, fourth = st.columns(4)
    name_filter = first.text_input("Student name", placeholder="Search by name")
    grades_list = load_grades(load_topics(), CONFIG)
    grade_filter = second.selectbox("Grade", ["All grades"] + grades_list)
    subject_filter = third.selectbox("Subject", ["All subjects"] + SUBJECT_CATALOG)
    topic_source = [row for row in rows if (not name_filter or name_filter.lower() in row["student_name"].lower()) and (grade_filter == "All grades" or row["grade"] == grade_filter) and (subject_filter == "All subjects" or row["subject"] == subject_filter)]
    topic_filter = fourth.selectbox("Topic", ["All topics"] + sorted({row["topic"] for row in topic_source if row["topic"]}))

filtered = [row for row in topic_source if topic_filter == "All topics" or row["topic"] == topic_filter]

if not filtered:
    st.info("No results match these filters.")
else:
    st.markdown(f"**{len(filtered)} result(s)**")
    for row in filtered:
        ended = format_local_time(row["end_time"])
        overall_time = format_exam_duration(row["start_time"], row["end_time"])
        with st.expander(f"{row['student_name']} · {row['subject']} · {row['score']}% · {ended}"):
            metrics = st.columns([1.3, 1, 1, 1, 1, 1.3])
            metrics[0].metric("Grade", str(row["grade"]).removeprefix("Grade ").strip() or str(row["grade"]))
            metrics[1].metric("Score", f"{row['score']}%")
            metrics[2].metric("Correct", row["correct_count"])
            metrics[3].metric("Wrong", row["wrong_count"])
            metrics[4].metric("Questions", row["question_count"])
            metrics[5].metric("Overall time", overall_time)
            location = f"{row['country']} · {row['school_state']} · {row['school_district']}" if row["school_district"] else row["country"]
            topic = f" · Topic: {row['topic']}" if row["topic"] else ""
            st.caption(f"Location: {location}{topic} · Time limit: {row['time_limit']} minutes · Completed: {ended}")
            review = json.loads(row["questions_json"])
            table_rows = "".join(
                f"<tr><td>{index}</td><td>{escape(str(item['question']))}</td><td>{format_options(item.get('options'))}</td><td>{escape(str(item.get('student_answer') or 'Not answered'))}</td><td>{escape(str(item['answer']))}</td><td>{format_question_time(item.get('time_seconds', 0))}</td><td>{'Correct' if item.get('student_answer') == item['answer'] else 'Wrong'}</td></tr>"
                for index, item in enumerate(review, 1)
            )
            st.markdown(
                f'<table class="results-table"><thead><tr><th>#</th><th>Question</th><th>Options</th><th>Student answer</th><th>Correct answer</th><th>Time</th><th>Status</th></tr></thead><tbody>{table_rows}</tbody></table>',
                unsafe_allow_html=True,
            )
            confirm_delete = st.checkbox("Confirm deletion", key=f"confirm_delete_{row['id']}")
            if st.button("Delete this test", key=f"delete_{row['id']}", disabled=not confirm_delete):
                delete_connection = sqlite3.connect(DB_PATH)
                delete_connection.execute("DELETE FROM exams WHERE id = ?", (row["id"],))
                delete_connection.commit()
                delete_connection.close()
                st.success("Test deleted.")
                st.rerun()
