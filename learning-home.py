from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from html import escape
from typing import Any

import streamlit as st
from streamlit_autorefresh import st_autorefresh

import storage
from llm_backend import DEFAULT_SUBJECTS, describe_topic_source, generate_questions as generate_questions_from_backend, load_config, load_grades, load_locations, load_models, load_topics, resolve_subjects, resolve_topics

TOPICS = load_topics()
CONFIG = load_config()
DEFAULTS = CONFIG["defaults"]
LOCATIONS = load_locations()
COUNTRIES = list(LOCATIONS.keys())
GRADE_OPTIONS = load_grades(TOPICS, CONFIG)
QUESTION_COUNTS = [5, 10, 15, 20, 25, 30]
STATE_PLACEHOLDER = "Select a state"
DISTRICT_PLACEHOLDER = "Select a school district"
VISUALS_BY_SUBJECT = {
    "Maths": ("https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=1200&q=80", "Maths visual"),
    "English": ("https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=1200&q=80", "Books and reading"),
    "Science": ("https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=1200&q=80", "Science laboratory"),
    "General Knowledge": ("https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=1200&q=80", "World map"),
    "Others": ("https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80", "Learning and discovery"),
}

st.set_page_config(page_title="Study Sprint", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")


def inject_styles(theme: str) -> None:
    dark_theme = """
        :root { --ink:#f6f7ff; --muted:#c2cbe0; --paper:#182238; --card:#222e49; --line:#455473; --sky:#5bbce8; --sun:#f6c94c; }
        .stApp { background:linear-gradient(120deg, #17223a 0%, #24334e 48%, #193b42 100%); }
        .hero h1, h1, h2, h3, .stMarkdown, .stMarkdown p, .stCaption, label, label p { color:#f6f7ff !important; }
        .pill { background:#263653; color:#f6f7ff; }
        .question-panel, .result-panel { background:#222e49dd; border-color:#455473; box-shadow:0 18px 50px rgba(0,0,0,.24); }
        div[data-testid="stForm"] { background:#222e49; border:2px solid #5bbce8; border-radius:14px; padding:1.25rem; }
        .stButton > button, .stFormSubmitButton > button { background:#f6c94c; color:#17223a; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#ff927d; color:#17223a; }
        div[data-testid="stMetric"] { background:#263653; border-color:#f6c94c; }
        div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] { color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; }
        .clock-time { color:#f6f7ff !important; }
        .clock-zone, .clock-date { color:#c2cbe0 !important; }
        .stRadio label { background:#263653; border-color:#5bbce8; color:#f6f7ff; }
        .stRadio label:hover { border-color:#ff927d; background:#3b3d56; }
        .stSelectbox [data-baseweb="select"], .stTextInput input, .stNumberInput input { background:#263653; color:#f6f7ff; border-color:#5bbce8; }
        .stSelectbox [data-baseweb="select"] * { color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; opacity:1 !important; }
        .stSelectbox [data-baseweb="select"] svg { opacity:0 !important; }
        .stSelectbox [data-baseweb="select"] { position:relative; padding-right:2.2rem; }
        .stSelectbox [data-baseweb="select"]::after { content:"▾"; position:absolute; right:.75rem; top:50%; transform:translateY(-50%); color:#bde8ff; font-size:1.1rem; font-weight:700; line-height:1; pointer-events:none; }
        .stTextInput input::placeholder, .stNumberInput input::placeholder { color:#c2cbe0; opacity:1; }
        div[role="listbox"], div[role="option"], [data-baseweb="popover"] { background:#263653; color:#f6f7ff; }
        div[role="option"] * { color:#f6f7ff !important; }
        [data-testid="stAlert"] { color:#f6f7ff; }
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] * { color:#f6f7ff !important; }
        .success-box { background:#51471f; border-color:#f6c94c; color:#fff8d7; }
        section[data-testid="stSidebar"] { background:#17223a !important; }
        section[data-testid="stSidebar"] .stSelectbox label, section[data-testid="stSidebar"] .stSlider label { color:#f6f7ff !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] { background:#263653 !important; border:2px solid #5bbce8; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * { background-color:#263653 !important; color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; }
        section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span { background:transparent !important; }
        section[data-testid="stSidebar"] .stSelectbox .react-aria-ComboBox > div { background:#263653 !important; border:2px solid #5bbce8 !important; border-radius:10px; }
        section[data-testid="stSidebar"] .stSelectbox input[role="combobox"] { background:#263653 !important; color:#f6f7ff !important; -webkit-text-fill-color:#f6f7ff !important; }
        section[data-testid="stSidebar"] .stSelectbox button[aria-label="Open"] { background:#314563 !important; color:#bde8ff !important; }
        section[data-testid="stSidebar"] .stSelectbox button[aria-label="Open"] svg { color:#bde8ff !important; fill:#bde8ff !important; stroke:#bde8ff !important; }
        section[data-testid="stSidebar"] [data-baseweb="popover"], section[data-testid="stSidebar"] [role="option"] { background:#263653 !important; color:#f6f7ff !important; }
        section[data-testid="stSidebar"] [role="option"] * { color:#f6f7ff !important; }
    """ if theme == "Dark" else ""
    css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root { --ink:#17324d; --muted:#526879; --paper:#fffaf0; --card:#ffffff; --mint:#b9efd0; --coral:#ff8f7a; --sun:#ffd86b; --sky:#bde8ff; --line:#d6e5eb; }
        html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); font-size:1.04rem; }
        .stApp { background:linear-gradient(120deg, #fff4cf 0%, #dff3ff 48%, #e4f8eb 100%); }
        h1, h2, h3 { font-family:'Space Grotesk', sans-serif !important; letter-spacing:0 !important; }
        .block-container { max-width:1100px; padding:3.2rem 2rem 4rem; }
        .brand { display:flex; justify-content:space-between; align-items:center; margin-bottom:3.5rem; }
        .brand-mark { font-family:'Space Grotesk'; font-weight:700; font-size:1.4rem; letter-spacing:0; }
        .brand-mark span { color:#f06f5d; }
        .eyebrow { color:#e85d4a; font-size:.88rem; font-weight:700; text-transform:uppercase; letter-spacing:.12em; }
        .hero h1 { font-size:clamp(3rem, 7vw, 5.5rem); line-height:.98; max-width:720px; margin:.55rem 0 1.1rem; color:#17324d; }
        .hero p { color:var(--muted); font-size:1.2rem; max-width:600px; line-height:1.6; }
        .pill { border:2px solid #79bfdc; background:#fff; border-radius:30px; padding:.6rem .9rem; color:var(--ink); font-size:.95rem; font-weight:600; }
        .question-panel, .result-panel { background:#fff; border:2px solid #b7d4df; border-radius:12px; padding:1.5rem; box-shadow:0 18px 50px rgba(35,68,91,.12); }
        .stButton > button, .stFormSubmitButton > button { border-radius:12px; border:0; background:#ef705c; color:white; font-size:1.05rem; font-weight:700; min-height:3.2rem; }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background:#ef705c; color:white; }
        div[data-testid="stMetric"] { background:#fff; border:2px solid var(--sun); border-radius:12px; padding:1.15rem; }
        div[data-testid="stMetricLabel"] { font-size:1rem; }
        div[data-testid="stMetricValue"] { font-size:1.8rem; }
        .timer { font-family:'Space Grotesk'; font-size:2.8rem; font-weight:700; color:#e85d4a; text-align:right; }
        .timer-label { color:var(--muted); font-size:.95rem; text-align:right; }
        .clock { text-align:right; margin-bottom:.4rem; }
        .clock-time { font-family:'Space Grotesk'; font-size:1.6rem; font-weight:700; color:#17324d; line-height:1.1; }
        .clock-zone { color:var(--muted); font-size:.82rem; font-weight:700; letter-spacing:.06em; }
        .clock-date { color:var(--muted); font-size:.78rem; }
        .question-index { color:#e85d4a; font-size:.95rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em; }
        .question-text { font-family:'Space Grotesk'; font-size:clamp(1.6rem, 3.4vw, 2.35rem); line-height:1.2; margin:.65rem 0 1.8rem; }
        .stRadio > div { gap:.55rem; }
        .stRadio label { background:#fff; border:2px solid #79bfdc; border-radius:12px; padding:.9rem 1rem; font-size:1.08rem; }
        .stRadio label:hover { border-color:#ef705c; background:#fff4d1; }
        .stSelectbox label, .stTextInput label, .stNumberInput label { font-size:1.05rem !important; font-weight:700; }
        .stSelectbox [data-baseweb="select"], .stTextInput input, .stNumberInput input { background:#fff; border:2px solid #79bfdc; color:var(--ink); font-size:1.05rem; }
        .stSelectbox [data-baseweb="select"] * { color:#17324d !important; -webkit-text-fill-color:#17324d !important; opacity:1 !important; }
        .stSelectbox [data-baseweb="select"] svg { opacity:0 !important; }
        .stSelectbox [data-baseweb="select"] { position:relative; padding-right:2.2rem; }
        .stSelectbox [data-baseweb="select"]::after { content:"▾"; position:absolute; right:.75rem; top:50%; transform:translateY(-50%); color:#17324d; font-size:1.1rem; font-weight:700; line-height:1; pointer-events:none; }
        .success-box { background:#fff0b8; border:2px solid #f3bd35; padding:1.3rem 1.5rem; border-radius:14px; font-size:1.15rem; }
        .celebration { color:#e85d4a; font-family:'Space Grotesk'; font-size:1.3rem; font-weight:700; text-align:center; margin:.7rem 0 1.3rem; }
        .footer-note { color:var(--muted); font-size:.9rem; text-align:center; margin-top:3rem; }
        """ + dark_theme + "\n        </style>"
    st.markdown(
        css,
        unsafe_allow_html=True,
    )


def save_question_set(student_name: str, grade: str, subject: str, topic: str, questions: list[dict[str, Any]]) -> int:
    """Store a generated question set and return its id.

    ``RETURNING id`` reads the new row's key on SQLite and on PostgreSQL alike.
    """
    question_set_id = storage.execute(
        "INSERT INTO question_sets (student_name, grade, subject, topic, questions_json, created_at)"
        " VALUES (:student_name, :grade, :subject, :topic, :questions_json, :created_at)"
        " RETURNING id",
        {
            "student_name": student_name,
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "questions_json": json.dumps(questions),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return int(question_set_id or 0)


def attach_visuals(questions: list[dict[str, Any]], subject: str, topic: str, enabled: bool) -> list[dict[str, Any]]:
    if not enabled or not questions:
        return questions
    visual = VISUALS_BY_SUBJECT.get(subject)
    if not visual:
        return questions
    image_count = max(1, round(len(questions) * 0.3))
    randomizer = random.Random(f"{subject}:{topic}:{len(questions)}")
    selected_indexes = set(randomizer.sample(range(len(questions)), min(image_count, len(questions))))
    for index, question in enumerate(questions):
        if index in selected_indexes:
            question["image_url"] = visual[0]
            question["image_alt"] = f"{visual[1]} for {topic}" if topic else visual[1]
    return questions


def reset_exam() -> None:
    for key in ("exam", "answers", "question_times", "question_started_at", "practice_feedback", "current_question", "exam_submitted", "celebration_shown"):
        st.session_state.pop(key, None)


def record_current_question_time() -> None:
    started_at = st.session_state.get("question_started_at")
    if started_at is None:
        return
    current = st.session_state.current_question
    elapsed = max(0.0, time.time() - started_at)
    st.session_state.question_times[current] = st.session_state.question_times.get(current, 0.0) + elapsed
    st.session_state.question_started_at = time.time()


def format_duration(seconds: float) -> str:
    total_seconds = max(0, round(seconds))
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes}m {remaining:02d}s" if minutes else f"{remaining}s"


@st.fragment(run_every="1s")
def render_clock() -> None:
    """Show the current time in the timezone configured in config.json.

    The clock lives in its own fragment so only the clock redraws each second,
    and ``%Z`` reports the real abbreviation for the moment shown - EST/EDT for
    America/New_York, GMT/BST for Europe/London, IST for Asia/Kolkata, and so
    on, including that zone's daylight saving rules.
    """
    now = datetime.now(CONFIG["zone"])
    st.markdown(
        f'<div class="clock"><div class="clock-time">{now.strftime("%I:%M:%S %p").lstrip("0")}</div>'
        f'<div class="clock-zone">{now.strftime("%Z")} · {escape(str(CONFIG["timezone_label"]))}</div>'
        f'<div class="clock-date">{now.strftime("%a %d %b %Y")}</div></div>',
        unsafe_allow_html=True,
    )


def submit_exam() -> None:
    # Prevent multiple submissions
    if st.session_state.get("exam_submitted"):
        return
    
    record_current_question_time()
    exam = st.session_state.exam
    answers = st.session_state.answers
    correct = sum(answers.get(index) == question["answer"] for index, question in enumerate(exam["questions"]))
    ended = datetime.now(timezone.utc)
    record = {
        "student_name": exam["student_name"], "grade": exam["grade"], "country": exam["country"], "school_state": exam["school_state"], "school_district": exam["school_district"], "subject": exam["subject"], "topic": exam["topic"], "question_set_id": exam["question_set_id"],
        "question_count": len(exam["questions"]), "time_limit": exam["time_limit"], "start_time": exam["start_time"],
        "end_time": ended.isoformat(), "score": round(correct / len(exam["questions"]) * 100), "correct_count": correct,
        "wrong_count": len(exam["questions"]) - correct,
        "questions_json": json.dumps([{**question, "student_answer": answers.get(index), "time_seconds": round(st.session_state.question_times.get(index, 0.0), 1)} for index, question in enumerate(exam["questions"])]),
    }
    storage.execute(
        "INSERT INTO exams (student_name, grade, country, school_state, school_district, subject, topic, question_set_id, question_count, time_limit, start_time, end_time, score, correct_count, wrong_count, questions_json)"
        " VALUES (:student_name, :grade, :country, :school_state, :school_district, :subject, :topic, :question_set_id, :question_count, :time_limit, :start_time, :end_time, :score, :correct_count, :wrong_count, :questions_json)",
        record,
    )
    st.session_state.result = record
    st.session_state.exam_submitted = True


def show_result() -> None:
    result = st.session_state.result
    if not st.session_state.get("celebration_shown", False):
        st.balloons()
        st.session_state.celebration_shown = True
    brand_left, brand_right = st.columns([3, 1])
    brand_left.markdown('<div class="eyebrow">Exam complete</div>', unsafe_allow_html=True)
    with brand_right:
        render_clock()
    st.markdown('<div class="celebration">🎉 Amazing work! ⭐ You made it to the finish line! 🎈</div>', unsafe_allow_html=True)
    st.title("You did it!")
    st.markdown(f'<div class="success-box"><strong>{result["student_name"]}</strong>, your result has been saved for parent review.</div>', unsafe_allow_html=True)
    st.write("")
    columns = st.columns(4)
    columns[0].metric("Score", f'{result["score"]}%')
    columns[1].metric("Correct", result["correct_count"])
    columns[2].metric("Wrong", result["wrong_count"])
    columns[3].metric("Subject", result["subject"])
    st.subheader("Answer review")
    for index, item in enumerate(json.loads(result["questions_json"]), start=1):
        student_answer = item.get("student_answer") or "Not answered"
        status = "Correct" if student_answer == item["answer"] else "Wrong"
        st.markdown(f"**{index}. {item['question']}**  \nYour answer: {student_answer} · Correct answer: {item['answer']} · Time: {format_duration(item.get('time_seconds', 0))} · **{status}**")
    if st.button("Start another exam", type="primary"):
        reset_exam()
        st.rerun()


def option_index(options: list[Any], preferred: Any, fallback: int = 0) -> int:
    """Index of the configured default value, or a fallback when it is absent."""
    try:
        return options.index(preferred)
    except ValueError:
        return fallback


def whole_number(value: Any, fallback: int) -> int:
    """Coerce a config value to an int, falling back when it is not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def show_setup() -> None:
    brand_left, brand_right = st.columns([3, 1])
    brand_left.markdown('<div class="brand"><div class="brand-mark">study<span>·</span>sprint</div><div class="pill">Student workspace</div></div>', unsafe_allow_html=True)
    with brand_right:
        render_clock()
    st.markdown('<div class="hero"><div class="eyebrow">Small steps, sharp thinking</div><h1>Your next best answer starts here.</h1><p>Build confidence with a focused, grade-aware quiz. Your progress is saved automatically so you can review it later.</p></div>', unsafe_allow_html=True)
    st.write("")
    country = st.selectbox("Country", COUNTRIES, index=option_index(COUNTRIES, DEFAULTS["country"]))
    country_states = LOCATIONS.get(country, {})
    if country_states:
        state_names = list(country_states.keys())
        state_options = [STATE_PLACEHOLDER] + state_names
        fallback_state = "North Carolina" if "North Carolina" in state_names else (state_names[0] if state_names else "")
        school_state = st.selectbox("State", state_options, index=option_index(state_options, DEFAULTS["state"], fallback=option_index(state_options, fallback_state)))
    else:
        school_state = ""

    districts = country_states.get(school_state, []) if school_state and school_state != STATE_PLACEHOLDER else []
    if country_states and districts:
        district_options = [DISTRICT_PLACEHOLDER] + districts
        school_district = st.selectbox("School District", district_options, index=option_index(district_options, DEFAULTS["school_district"], fallback=1 if districts else 0))
    elif country_states and school_state and school_state != STATE_PLACEHOLDER:
        district_options = [DISTRICT_PLACEHOLDER]
        school_district = st.selectbox("School District", district_options, index=0)
    else:
        school_district = ""

    grade = st.selectbox("Grade", GRADE_OPTIONS, index=option_index(GRADE_OPTIONS, DEFAULTS["grade"]))
    subject_options = resolve_subjects(TOPICS, grade, school_district)
    subject = st.selectbox("Subject", subject_options, index=option_index(subject_options, DEFAULTS["subject"]))
    topic_options = resolve_topics(TOPICS, subject, grade, school_district)
    if topic_options:
        topic = st.selectbox("Topic", topic_options, index=option_index(topic_options, DEFAULTS.get("topic")), key="topic_select")
        source_label = describe_topic_source(TOPICS, subject, grade, school_district)
        st.caption(f"Topics for {source_label} from config/topics.json." if source_label else "Topics from config/topics.json.")
    else:
        topic = st.text_input("Topic", placeholder="e.g. World War II or Photography", key="topic_custom")
    topic_value = (topic or "").strip()
    include_images = st.toggle("Include visual questions", value=bool(DEFAULTS["include_images"]), help="Adds visuals to about 30% of applicable questions.")
    practice_mode = st.toggle("Practice mode", value=bool(DEFAULTS["practice_mode"]), help="Shows the correct answer after each question and moves forward only.")
    with st.form("exam_setup"):
        first, second = st.columns(2)
        name = first.text_input("Student name", placeholder="e.g. Alex Morgan")
        count = first.selectbox("Number of questions", QUESTION_COUNTS, index=option_index(QUESTION_COUNTS, whole_number(DEFAULTS["question_count"], QUESTION_COUNTS[0])))
        minutes = second.number_input("Time limit (minutes)", min_value=1, max_value=180, value=min(180, max(1, whole_number(DEFAULTS["time_limit"], 10))), step=1)
        submitted = st.form_submit_button("Start exam →", use_container_width=True)
    if submitted:
        if not name.strip():
            st.error("Please enter a student name to begin.")
            return
        if country_states:
            if school_state == STATE_PLACEHOLDER:
                st.error("Please select a state to begin.")
                return
            if not districts:
                st.error("No district catalog entries are available for this state yet.")
                return
            if school_district == DISTRICT_PLACEHOLDER:
                st.error("Please select a school district to begin.")
                return
        if not topic_value:
            st.error("Please enter a topic for the custom subject." if subject == "Others" else "Please select a topic to begin.")
            return
        with st.spinner("Preparing your questions..."):
            try:
                questions, source = generate_questions_from_backend(selected_model, subject, grade, count, school_state, school_district, topic_value, name.strip(), temperature, include_images)
            except RuntimeError as error:
                st.error(str(error))
                return
        questions = attach_visuals(questions, subject, topic_value, include_images)
        question_set_id = save_question_set(name.strip(), grade, subject, topic_value, questions)
        st.session_state.exam = {"student_name": name.strip(), "grade": grade, "country": country, "school_state": school_state, "school_district": school_district, "subject": subject, "topic": topic_value, "include_images": include_images, "practice_mode": practice_mode, "question_set_id": question_set_id, "time_limit": int(minutes), "questions": questions, "start_time": datetime.now(timezone.utc).isoformat(), "deadline": time.time() + int(minutes) * 60, "source": source}
        st.session_state.answers = {}
        st.session_state.question_times = {}
        st.session_state.question_started_at = None
        st.session_state.practice_feedback = False
        st.session_state.current_question = 0
        st.session_state.exam_submitted = False
        st.rerun()


def show_exam() -> None:
    exam = st.session_state.exam
    if st.session_state.get("exam_submitted"):
        show_result()
        return
    st_autorefresh(interval=1000, key="exam_clock")
    current = st.session_state.current_question
    if "question_times" not in st.session_state:
        st.session_state.question_times = {}
    if st.session_state.get("question_started_at") is None:
        st.session_state.question_started_at = time.time()
    visible_answer = st.session_state.get(f"answer_{current}")
    if visible_answer:
        st.session_state.answers[current] = visible_answer
    seconds_left = max(0, int(exam["deadline"] - time.time()))
    if seconds_left == 0:
        submit_exam()
        st.rerun()
    question = exam["questions"][current]
    minutes, seconds = divmod(seconds_left, 60)
    top_left, top_right = st.columns([3, 1])
    exam_details = " · ".join(escape(str(value)) for value in (exam["student_name"], exam["grade"], exam["subject"], exam["topic"]) if value)
    top_left.markdown(f'<div class="brand"><div class="brand-mark">study<span>·</span>sprint</div><div class="pill">{exam_details}</div></div>', unsafe_allow_html=True)
    with top_right:
        render_clock()
        st.markdown(f'<div class="timer">{minutes:02d}:{seconds:02d}</div><div class="timer-label">remaining</div>', unsafe_allow_html=True)
    st.progress((current + 1) / len(exam["questions"]))
    st.markdown(f'<div class="question-panel"><div class="question-index">Question {current + 1} of {len(exam["questions"])}</div><div class="question-text">{question["question"]}</div>', unsafe_allow_html=True)
    if question.get("image_url"):
        st.image(question["image_url"], caption=question.get("image_alt", "Question visual"), use_container_width=True)
    previous_answer = st.session_state.answers.get(current)
    options = question["options"]
    selected = st.radio("Choose one answer", options, index=options.index(previous_answer) if previous_answer in options else None, key=f"answer_{current}", label_visibility="collapsed")
    feedback_shown = st.session_state.get("practice_feedback", False)
    if exam.get("practice_mode") and feedback_shown:
        if selected == question["answer"]:
            st.success("Correct! Great thinking.")
        else:
            st.error(f"Not quite. The correct answer is: {question['answer']}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")
    left, middle, right = st.columns([1, 1, 1])
    if current > 0 and not exam.get("practice_mode") and left.button("← Previous", use_container_width=True):
        record_current_question_time()
        st.session_state.answers[current] = selected
        st.session_state.current_question -= 1
        st.session_state.question_started_at = time.time()
        st.rerun()
    if exam.get("practice_mode"):
        action_label = "Finish exam" if current == len(exam["questions"]) - 1 and feedback_shown else "Continue →" if feedback_shown else "Check answer"
        if middle.button(action_label, type="primary", use_container_width=True):
            if not selected:
                st.warning("Choose an answer before continuing.")
            elif not feedback_shown:
                st.session_state.answers[current] = selected
                st.session_state.practice_feedback = True
                st.rerun()
            elif current < len(exam["questions"]) - 1:
                record_current_question_time()
                st.session_state.current_question += 1
                st.session_state.practice_feedback = False
                st.session_state.question_started_at = time.time()
                st.rerun()
            else:
                record_current_question_time()
                submit_exam()
                st.rerun()
    elif current < len(exam["questions"]) - 1 and middle.button("Next →", type="primary", use_container_width=True):
        record_current_question_time()
        st.session_state.answers[current] = selected
        st.session_state.current_question += 1
        st.session_state.question_started_at = time.time()
        st.rerun()
    # Only show submit button if exam is not already submitted
    if not exam.get("practice_mode") and current == len(exam["questions"]) - 1 and not st.session_state.get("exam_submitted") and right.button("Submit exam", type="primary", use_container_width=True):
        record_current_question_time()
        st.session_state.answers[current] = selected
        submit_exam()
        st.rerun()
    st.caption(f"Questions are generated using {exam['source']}.")


theme = st.sidebar.radio("Appearance", ["Light", "Dark"], index=option_index(["Light", "Dark"], DEFAULTS["appearance"], fallback=1), horizontal=True, key="appearance")
for message in CONFIG["warnings"]:
    st.sidebar.warning(message)
configured_models = load_models()
if not configured_models:
    st.sidebar.error("No enabled models found in config/models.json.")
    st.stop()
selected_model_name = st.sidebar.selectbox("LLM model", [model["name"] for model in configured_models], index=0, help="Models are configured in config/models.json.")
selected_model = configured_models[[model["name"] for model in configured_models].index(selected_model_name)]
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1, help="Lower values are more consistent; higher values create more variety.")
st.sidebar.caption("Enable or disable models in config/models.json.")
st.sidebar.caption(f"Clock: {CONFIG['timezone']} ({CONFIG['timezone_label']}) from config/config.json.")
st.sidebar.caption("Field defaults come from config/config.json; subjects and topics from config/topics.json.")
storage.ensure_schema()
st.sidebar.caption(f"Results storage: {storage.backend_label()}.")
if not storage.is_hosted():
    st.sidebar.info("Results are stored in a local file that a hosted container may discard. Set DATABASE_URL to a PostgreSQL URL to keep them permanently.")
inject_styles(theme)
if "exam" not in st.session_state:
    show_setup()
else:
    show_exam()
