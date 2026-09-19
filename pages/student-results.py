from __future__ import annotations

import json
from html import escape
from datetime import datetime, timezone

import streamlit as st

from backend.services import storage
from backend.services.llm_backend import (
    load_config,
    load_grades,
    load_locations,
    load_topics,
    resolve_subjects,
    resolve_topics,
)
from backend.services.auth_storage import get_students_by_parent, get_exams_by_parent
from backend.services.logging_config import get_logger
from middleware import (
    require_parent_auth,
    logout_parent,
    get_current_parent,
    set_current_student,
    get_current_student,
)
from ui.components.theme import inject_parent_theme
from ui.components.appearance import render_appearance_toggle

logger = get_logger(__name__)

TOPIC_CATALOG = load_topics()
SUBJECT_CATALOG = list(TOPIC_CATALOG["subjects"])
CONFIG = load_config()
LOCATIONS = load_locations()
COUNTRIES = list(LOCATIONS.keys())
DEFAULTS = CONFIG.get("defaults", {})


def topics_for_subject(subject: str, grade: str, school_district: str) -> list[str]:
    """All configured topics for a Subject."""
    if subject and subject != "All subjects":
        return resolve_topics(TOPIC_CATALOG, subject, grade, school_district)

    combined: set[str] = set()
    for name in SUBJECT_CATALOG:
        combined.update(resolve_topics(TOPIC_CATALOG, name, grade, school_district))
    return sorted(combined)


def format_question_time(seconds: float) -> str:
    total_seconds = max(0, round(float(seconds or 0)))
    minutes, remaining = divmod(total_seconds, 60)
    return f"{minutes}m {remaining:02d}s" if minutes else f"{remaining}s"


def format_exam_duration(start_time: str, end_time: str) -> str:
    try:
        seconds = (
            datetime.fromisoformat(end_time)
            - datetime.fromisoformat(start_time)
        ).total_seconds()
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
    if not options:
        return "—"
    return "<br>".join(
        f"{letter}) {escape(str(option))}"
        for letter, option in zip("ABCDEFGH", options)
    )


# Streamlit page setup
st.set_page_config(
    page_title="Student Results · Study Sprint",
    page_icon="📊",
    layout="wide",
)

theme = render_appearance_toggle(default=DEFAULTS.get("appearance", "Dark"))
inject_parent_theme(theme)

st.markdown(
    '<div class="brand">study<span>·</span>sprint / student results</div>',
    unsafe_allow_html=True,
)

require_parent_auth()

# Get current parent and students
parent = get_current_parent()
students = get_students_by_parent(parent["id"]) if parent else []

# Student selection
if students:
    student_options = {
        f"{s['student_name']} ({s['student_id']})": s["student_id"]
        for s in students
    }

    current_student_id = get_current_student()

    if not current_student_id:
        default_student = students[0]["student_id"]
        set_current_student(default_student)
        current_student_id = default_student

    current_display = next(
        (name for name, sid in student_options.items() if sid == current_student_id),
        list(student_options.keys())[0],
    )

    col1, col2, col3, col4 = st.columns([3, 1, 1, 1], vertical_alignment="bottom")

    with col1:
        selected_student_display = st.selectbox(
            "Select Student",
            options=list(student_options.keys()),
            index=list(student_options.keys()).index(current_display),
            key="student_selector",
        )

        if selected_student_display != current_display:
            set_current_student(student_options[selected_student_display])
            st.rerun()

    with col2:
        if st.button("👤 Parent Profile", use_container_width=True):
            st.switch_page("pages/parent-profile.py")

    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    with col4:
        if st.button("🚪 Sign out", use_container_width=True):
            logout_parent()

else:
    st.info("No students registered yet. Please register a student first.")
    if st.button("Register Student"):
        st.switch_page("pages/parent-login.py")
    st.stop()

header_left, header_right = st.columns([4, 1])
header_left.markdown("## Student Results")
header_left.caption(f"Review completed exams for {selected_student_display}.")

if st.button("▶️ Start a New Exam", type="primary"):
    st.switch_page("learning-home.py")

# Load exam results
current_student_id = get_current_student()
rows = (
    get_exams_by_parent(parent["id"], current_student_id)
    if current_student_id
    else []
)

if not rows:
    st.info("No exam results yet for this student.")
    st.stop()

# Filters
with st.container(border=True):
    st.markdown("#### Filter results")

    first, second, third = st.columns(3)
    fourth, fifth, sixth = st.columns(3)

    grades_list = load_grades(load_topics(), CONFIG)

    default_country = DEFAULTS.get(
        "country",
        COUNTRIES[0] if COUNTRIES else "United States",
    )
    country_index = (
        COUNTRIES.index(default_country)
        if default_country in COUNTRIES
        else 0
    )
    country_filter = first.selectbox("Country", COUNTRIES, index=country_index)

    country_states = LOCATIONS.get(country_filter, {})
    state_names = list(country_states.keys())

    if state_names:
        default_state = DEFAULTS.get("state", state_names[0])
        state_options = ["All states"] + state_names
        state_index = (
            state_options.index(default_state)
            if default_state in state_options
            else 0
        )
        state_filter = second.selectbox("State", state_options, index=state_index)
    else:
        state_filter = "All states"
        second.selectbox("State", ["All states"], index=0, disabled=True)

    grade_options = ["All grades"] + grades_list
    grade_filter = third.selectbox("Grade", grade_options, index=0)

    subject_options = ["All subjects"] + SUBJECT_CATALOG
    subject_filter = fourth.selectbox("Subject", subject_options, index=0)

    topic_catalog = topics_for_subject(
        subject_filter,
        "" if grade_filter == "All grades" else grade_filter,
        "",
    )
    topic_options = ["All topics"] + topic_catalog

    previous_subject = st.session_state.get("results_topic_subject")
    previous_grade = st.session_state.get("results_topic_grade")

    subject_or_grade_changed = (
        previous_subject != subject_filter
        or previous_grade != grade_filter
    )

    if subject_or_grade_changed or st.session_state.get("results_topic_filter") not in topic_options:
        st.session_state.results_topic_subject = subject_filter
        st.session_state.results_topic_grade = grade_filter
        st.session_state.results_topic_filter = "All topics"

    topic_filter = fifth.selectbox(
        "Topic",
        topic_options,
        key="results_topic_filter",
    )

    # Apply filters
    filtered = rows

    if country_filter != "All countries":
        filtered = [row for row in filtered if row.get("country") == country_filter]

    if state_filter != "All states":
        filtered = [
            row for row in filtered if row.get("school_state") == state_filter
        ]

    if grade_filter != "All grades":
        filtered = [row for row in filtered if row["grade"] == grade_filter]

    if subject_filter != "All subjects":
        filtered = [row for row in filtered if row["subject"] == subject_filter]

    if topic_filter != "All topics":
        filtered = [row for row in filtered if row.get("topic") == topic_filter]

if not filtered:
    st.info("No results match these filters.")
else:
    st.markdown(f"**{len(filtered)} result(s)**")

    for row in filtered:
        ended = format_local_time(row["end_time"])
        overall_time = format_exam_duration(row["start_time"], row["end_time"])

        with st.expander(
            f"{row['student_name']} · {row['subject']} · {row['score']}% · {ended}"
        ):
            metrics = st.columns([1.3, 1, 1, 1, 1, 1.3])
            metrics[0].metric(
                "Grade",
                str(row["grade"]).removeprefix("Grade ").strip()
                or str(row["grade"]),
            )
            metrics[1].metric("Score", f"{row['score']}%")
            metrics[2].metric("Correct", row["correct_count"])
            metrics[3].metric("Wrong", row["wrong_count"])
            metrics[4].metric("Questions", row["question_count"])
            metrics[5].metric("Overall time", overall_time)

            location = (
                f"{row['country']} · {row['school_state']} · {row['school_district']}"
                if row["school_district"]
                else row["country"]
            )
            topic = f" · Topic: {row['topic']}" if row["topic"] else ""

            st.caption(
                f"Location: {location}{topic} · Time limit: {row['time_limit']} minutes · Completed: {ended}"
            )

            review = json.loads(row["questions_json"])

            table_rows = "".join(
                f"<tr>"
                f"<td>{index}</td>"
                f"<td>{escape(str(item['question']))}</td>"
                f"<td>{format_options(item.get('options'))}</td>"
                f"<td>{escape(str(item.get('student_answer') or 'Not answered'))}</td>"
                f"<td>{escape(str(item['answer']))}</td>"
                f"<td>{format_question_time(item.get('time_seconds', 0))}</td>"
                f"<td>{'Correct' if item.get('student_answer') == item['answer'] else 'Wrong'}</td>"
                f"</tr>"
                for index, item in enumerate(review, 1)
            )

            st.markdown(
                f"""
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Question</th>
                            <th>Options</th>
                            <th>Student answer</th>
                            <th>Correct answer</th>
                            <th>Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )

            confirm_delete = st.checkbox(
                "Confirm deletion", key=f"confirm_delete_{row['id']}"
            )

            if st.button(
                "Delete this test",
                key=f"delete_{row['id']}",
                disabled=not confirm_delete,
            ):
                storage.execute(
                    "DELETE FROM exams WHERE id = :id",
                    {"id": row["id"]},
                )
                logger.info(
                    "Deleted exam id %s for student '%s'.",
                    row["id"],
                    row["student_name"],
                )
                st.success("Test deleted.")
                st.rerun()