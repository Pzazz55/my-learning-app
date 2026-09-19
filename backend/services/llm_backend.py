from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from backend.services import storage
from app_settings import BASE_DIR, read_setting

CONFIG_DIR = BASE_DIR / "config"


def _resolve_config_path(filename: str) -> Path:
    """Return the path to a config file, checking config/ first with root fallback."""
    in_config_dir = CONFIG_DIR / filename
    if in_config_dir.exists():
        return in_config_dir
    return BASE_DIR / filename


MODELS_PATH = _resolve_config_path("models.json")
TOPICS_PATH = _resolve_config_path("topics.json")
CONFIG_PATH = _resolve_config_path("config.json")
LOCATIONS_PATH = _resolve_config_path("locations.json")
DEFAULT_CONFIG: dict[str, Any] = {
    "timezone": "America/New_York",
    "timezone_label": "Eastern Time",
    "defaults": {
        "country": "United States",
        "state": "North Carolina",
        "school_district": "Charlotte-Mecklenburg Schools",
        "grade": "Grade 1",
        "subject": "Maths",
        "topic": "",
        "question_count": 5,
        "time_limit": 10,
        "include_images": False,
        "practice_mode": False,
        "appearance": "Dark",
    },
}


def load_models() -> list[dict[str, Any]]:
    path = _resolve_config_path("models.json")
    with path.open(encoding="utf-8") as file:
        models = json.load(file)
    available = []
    for model in models:
        if not model.get("enabled", True):
            continue
        key_name = model.get("api_key_env", "")
        key = read_setting(key_name)
        if key:
            available.append(model)
    return available


DEFAULT_LOCATIONS: dict[str, dict[str, list[str]]] = {
    "United States": {
        "North Carolina": ["Charlotte-Mecklenburg Schools", "Wake County Public School System"],
        "California": ["Los Angeles Unified School District", "San Diego Unified School District"],
    },
    "Canada": {},
    "United Kingdom": {},
    "Australia": {},
    "India": {},
    "Other": {},
}


def load_locations() -> dict[str, dict[str, list[str]]]:
    """Return the Country -> State -> [School Districts] mapping configured in locations.json."""
    try:
        path = _resolve_config_path("locations.json")
        with path.open(encoding="utf-8") as file:
            configured = json.load(file)
    except FileNotFoundError:
        return DEFAULT_LOCATIONS

    if not isinstance(configured, dict):
        return DEFAULT_LOCATIONS

    locations: dict[str, dict[str, list[str]]] = {}
    for country, states in configured.items():
        if not isinstance(country, str) or not isinstance(states, dict):
            continue
        cleaned_states: dict[str, list[str]] = {}
        for state, districts in states.items():
            if not isinstance(state, str):
                continue
            if isinstance(districts, list):
                cleaned_states[state] = [str(d) for d in districts if isinstance(d, (str, int))]
            else:
                cleaned_states[state] = []
        locations[country] = cleaned_states

    return locations or DEFAULT_LOCATIONS


def load_grades(topics_catalog: dict[str, Any] | None = None, config: dict[str, Any] | None = None) -> list[str]:
    """Return available grade options derived from topics.json or config.json."""
    if config and isinstance(config.get("grades"), list) and config["grades"]:
        return [str(g) for g in config["grades"]]

    grades_dict = (topics_catalog.get("grades") if topics_catalog else None) or {}
    if isinstance(grades_dict, dict) and grades_dict:
        import re

        def sort_key(label: str) -> tuple[int, str]:
            match = re.search(r"\d+", label)
            return (int(match.group()), label) if match else (0, label)

        return sorted(grades_dict.keys(), key=sort_key)

    return [f"Grade {number}" for number in range(1, 13)]


DEFAULT_SUBJECTS = ["Maths", "English", "Science", "General Knowledge", "Others"]


TOPIC_SECTIONS = ("schools", "default", "subjects", "grades")


def _require_mapping(section: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"topics.json '{section}' must be a JSON object.")
    return value


def load_topics() -> dict[str, Any]:
    """Return the topic catalog configured in topics.json.

    The file has two main sections:
        "schools": school district -> "Grade N" -> subject -> specific topic overrides
                   (e.g. "Charlotte-Mecklenburg Schools")
        "default": fallback values when a school/grade/subject has no specific entry,
                   or for schools outside configured districts:
                   "grades" -> "Grade N" -> subject -> topics
                   "subjects" -> subject -> topics (general/grade-independent fallback)

    Legacy sections ("grades", "subjects" at top level) are also supported for backward compatibility.
    A missing topics.json leaves the built-in subjects with free-text topics.
    """
    empty_catalog: dict[str, Any] = {
        "schools": {},
        "default": {},
        "grades": {},
        "subjects": {subject: [] for subject in DEFAULT_SUBJECTS},
    }
    try:
        path = _resolve_config_path("topics.json")
        with path.open(encoding="utf-8") as file:
            configured = json.load(file)
    except FileNotFoundError:
        return empty_catalog
    if not isinstance(configured, dict):
        raise ValueError("topics.json must contain a JSON object with 'schools' and 'default' sections.")
    unknown = sorted(set(configured) - set(TOPIC_SECTIONS))
    if unknown:
        raise ValueError(f"topics.json has unknown section(s): {', '.join(unknown)}. Use 'schools' and 'default'.")

    catalog: dict[str, Any] = {
        "schools": {},
        "default": {},
        "grades": {},
        "subjects": {},
    }

    if "schools" in configured:
        catalog["schools"] = _require_mapping("schools", configured["schools"])

    if "default" in configured:
        catalog["default"] = _require_mapping("default", configured["default"])

    default_obj = catalog["default"]
    grades_dict: dict[str, Any] = {}
    if isinstance(default_obj.get("grades"), dict):
        grades_dict = dict(default_obj["grades"])
    else:
        for key, value in default_obj.items():
            if isinstance(value, dict):
                grades_dict[key] = value

    if "grades" in configured and not grades_dict:
        grades_dict = _require_mapping("grades", configured["grades"])

    catalog["grades"] = grades_dict

    discovered_subjects: list[str] = []
    for subj in DEFAULT_SUBJECTS:
        if subj not in discovered_subjects:
            discovered_subjects.append(subj)

    for grade_data in grades_dict.values():
        if isinstance(grade_data, dict):
            for subj in grade_data:
                if subj not in discovered_subjects:
                    discovered_subjects.append(subj)

    for key, value in default_obj.items():
        if isinstance(value, list) and key not in discovered_subjects:
            discovered_subjects.append(key)

    top_subjects = configured.get("subjects") if isinstance(configured.get("subjects"), dict) else {}
    for subj in top_subjects:
        if subj not in discovered_subjects:
            discovered_subjects.append(subj)

    subjects_dict: dict[str, list[str]] = {}
    for subj in discovered_subjects:
        if isinstance(default_obj.get(subj), list):
            subjects_dict[subj] = default_obj[subj]
        elif isinstance(default_obj.get("subjects"), dict) and isinstance(default_obj["subjects"].get(subj), list):
            subjects_dict[subj] = default_obj["subjects"][subj]
        elif isinstance(top_subjects.get(subj), list):
            subjects_dict[subj] = top_subjects[subj]
        else:
            subjects_dict[subj] = []

    catalog["subjects"] = subjects_dict
    return catalog


def resolve_subjects(catalog: dict[str, Any], grade: str = "", school_district: str = "") -> list[str]:
    """Subject list for the current School -> Grade selection.

    Priority:
    1. Subjects defined for the school district's grade entry (school-specific)
    2. Subjects defined in the default grade entry
    3. Global default subject list from catalog["subjects"]
    """
    schools = catalog.get("schools") or {}
    school = schools.get(school_district) if isinstance(schools, dict) else None
    school_grade = school.get(grade) if isinstance(school, dict) else None

    default_obj = catalog.get("default") if isinstance(catalog.get("default"), dict) else {}
    default_grade = None
    if isinstance(default_obj.get("grades"), dict):
        default_grade = default_obj["grades"].get(grade)
    elif isinstance(default_obj.get(grade), dict):
        default_grade = default_obj.get(grade)
    elif isinstance(catalog.get("grades"), dict):
        default_grade = catalog["grades"].get(grade)

    # 1. School-specific subjects for this grade
    if isinstance(school_grade, dict):
        subjects = list(school_grade.keys())
        if subjects:
            return subjects

    # 2. Default grade subjects
    if isinstance(default_grade, dict):
        subjects = list(default_grade.keys())
        if subjects:
            return subjects

    # 3. Global subject list
    subjects_dict = catalog.get("subjects")
    if isinstance(subjects_dict, dict):
        return list(subjects_dict.keys())

    return DEFAULT_SUBJECTS


def resolve_topics(catalog: dict[str, Any], subject: str, grade: str = "", school_district: str = "") -> list[str]:
    """Topic list for the current School -> Grade -> Subject selection.

    The most specific entry wins:
    1. The school's own list for that grade and subject (e.g. "Charlotte-Mecklenburg Schools")
    2. The default grade list for that subject
    3. The default general subject list (e.g. "General Knowledge")
    An empty result keeps the free-text topic box, so a sparse file never blocks a test.
    """
    schools = catalog.get("schools") or {}
    school = schools.get(school_district) if isinstance(schools, dict) else None
    school_grade = school.get(grade) if isinstance(school, dict) else None

    default_obj = catalog.get("default") if isinstance(catalog.get("default"), dict) else {}
    default_grade = None
    if isinstance(default_obj.get("grades"), dict):
        default_grade = default_obj["grades"].get(grade)
    elif isinstance(default_obj.get(grade), dict):
        default_grade = default_obj.get(grade)
    elif isinstance(catalog.get("grades"), dict):
        default_grade = catalog["grades"].get(grade)

    # 1. School-specific override
    if isinstance(school_grade, dict):
        topics = school_grade.get(subject)
        if isinstance(topics, list) and topics:
            return [str(topic) for topic in topics]

    # 2. Default grade-specific topics
    if isinstance(default_grade, dict):
        topics = default_grade.get(subject)
        if isinstance(topics, list) and topics:
            return [str(topic) for topic in topics]

    # 3. Default general / grade-independent topics (e.g. General Knowledge)
    if isinstance(default_obj.get(subject), list) and default_obj[subject]:
        return [str(topic) for topic in default_obj[subject]]

    subjects_dict = default_obj.get("subjects") if isinstance(default_obj.get("subjects"), dict) else catalog.get("subjects")
    if isinstance(subjects_dict, dict):
        topics = subjects_dict.get(subject)
        if isinstance(topics, list) and topics:
            return [str(topic) for topic in topics]

    return []


def describe_topic_source(catalog: dict[str, Any], subject: str, grade: str = "", school_district: str = "") -> str:
    """Return a human-friendly description of where the topics came from."""
    schools = catalog.get("schools") or {}
    school = schools.get(school_district) if isinstance(schools, dict) else None
    school_grade = school.get(grade) if isinstance(school, dict) else None
    if isinstance(school_grade, dict) and isinstance(school_grade.get(subject), list) and school_grade[subject]:
        return f"{school_district} · {grade} · {subject}"

    default_obj = catalog.get("default") if isinstance(catalog.get("default"), dict) else {}
    default_grade = None
    if isinstance(default_obj.get("grades"), dict):
        default_grade = default_obj["grades"].get(grade)
    elif isinstance(default_obj.get(grade), dict):
        default_grade = default_obj.get(grade)
    elif isinstance(catalog.get("grades"), dict):
        default_grade = catalog["grades"].get(grade)

    if isinstance(default_grade, dict) and isinstance(default_grade.get(subject), list) and default_grade[subject]:
        if school_district and school_district != "Select a school district":
            return f"{grade} · {subject} (Default fallback for {school_district})"
        return f"{grade} · {subject} (Default)"

    if isinstance(default_obj.get(subject), list) and default_obj[subject]:
        return f"{subject} (Default)"

    subjects_dict = default_obj.get("subjects") if isinstance(default_obj.get("subjects"), dict) else catalog.get("subjects")
    if isinstance(subjects_dict, dict) and isinstance(subjects_dict.get(subject), list) and subjects_dict[subject]:
        return f"{subject} (Default)"

    return ""


def load_config() -> dict[str, Any]:
    """Return the app settings configured in config.json.

    Recognised keys are "timezone" (an IANA name), "timezone_label" (the clock
    caption) and "defaults" (the starting value of each field on the setup
    page). Anything unusable is described in the "warnings" list so the app can
    report it in the sidebar instead of refusing to start.
    """
    settings: dict[str, Any] = {key: value for key, value in DEFAULT_CONFIG.items() if key != "defaults"}
    settings["defaults"] = dict(DEFAULT_CONFIG["defaults"])
    warnings: list[str] = []
    try:
        path = _resolve_config_path("config.json")
        with path.open(encoding="utf-8") as file:
            configured = json.load(file)
    except FileNotFoundError:
        configured = {}
    if not isinstance(configured, dict):
        raise ValueError("config.json must contain a JSON object.")
    for key in ("timezone", "timezone_label"):
        value = configured.get(key)
        if isinstance(value, str) and value.strip():
            settings[key] = value.strip()
    unknown_top = sorted(set(configured) - set(DEFAULT_CONFIG))
    if unknown_top:
        warnings.append(f"config.json has unknown key(s): {', '.join(unknown_top)}.")
    supplied = configured.get("defaults")
    if supplied is not None:
        if not isinstance(supplied, dict):
            warnings.append("config.json 'defaults' must be a JSON object. The built-in defaults are used instead.")
        else:
            unknown_keys = sorted(set(supplied) - set(DEFAULT_CONFIG["defaults"]))
            if unknown_keys:
                warnings.append(f"config.json 'defaults' has unknown key(s): {', '.join(unknown_keys)}.")
            settings["defaults"].update({key: value for key, value in supplied.items() if key in DEFAULT_CONFIG["defaults"]})
    try:
        settings["zone"] = ZoneInfo(settings["timezone"])
    except (KeyError, ValueError):
        warnings.append(f"config.json timezone '{settings['timezone']}' is not a recognised IANA timezone. Falling back to {DEFAULT_CONFIG['timezone']}.")
        settings["timezone"] = DEFAULT_CONFIG["timezone"]
        settings["timezone_label"] = DEFAULT_CONFIG["timezone_label"]
        settings["zone"] = ZoneInfo(settings["timezone"])
    settings["warnings"] = warnings
    return settings


def unique_questions(questions: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for question in questions:
        key = " ".join(str(question.get("question", "")).lower().split())
        if key and key not in seen:
            seen.add(key)
            unique.append(question)
    return unique[:count]


def historical_mistakes(student_name: str, grade: str, subject: str, topic: str) -> list[str]:
    """Questions this student previously answered incorrectly for the same topic.

    The query uses named bind parameters so it runs unchanged on SQLite and on a
    hosted PostgreSQL database.
    """
    rows = storage.fetch_all(
        "SELECT questions_json FROM exams"
        " WHERE lower(student_name) = lower(:student_name)"
        " AND grade = :grade AND subject = :subject AND topic = :topic"
        " ORDER BY end_time DESC",
        {"student_name": student_name, "grade": grade, "subject": subject, "topic": topic},
    )
    mistakes: list[str] = []
    seen: set[str] = set()
    for row in rows:
        try:
            review = json.loads(row["questions_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        for item in review:
            if item.get("student_answer") and item.get("student_answer") != item.get("answer"):
                question = str(item.get("question", "")).strip()
                key = " ".join(question.lower().split())
                if question and key not in seen:
                    seen.add(key)
                    mistakes.append(question)
    return mistakes[:8]


def _api_key(model: dict[str, Any]) -> str:
    key_name = model.get("api_key_env", "")
    key = read_setting(key_name)
    if not key:
        raise RuntimeError(f"Missing API key. Add {key_name} to .env or the app's Streamlit secrets for {model['name']}.")
    return str(key)


def _request_text(model: dict[str, Any], prompt: str, temperature: float, max_tokens: int) -> str:
    provider = model["provider"].lower()
    model_id = model["model"]
    key = _api_key(model)
    if provider == "google":
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}",
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}},
            timeout=45,
        )
        response.raise_for_status()
        parts = response.json()["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    if provider in {"openai", "openrouter", "groq"}:
        endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
        }
        endpoint = endpoints[provider]
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if provider == "openrouter":
            headers.update({"HTTP-Referer": "http://localhost", "X-Title": "Study Sprint"})
        response = requests.post(
            endpoint,
            headers=headers,
            json={"model": model_id, "messages": [{"role": "user", "content": prompt}], "temperature": temperature, "max_tokens": max_tokens},
            timeout=45,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    if provider == "huggingface":
        response = requests.post(
            f"https://router.huggingface.co/hf-inference/models/{model_id}",
            headers={"Authorization": f"Bearer {key}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": min(512, max(256, max_tokens)), "temperature": temperature, "do_sample": temperature > 0}},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        return payload[0].get("generated_text", "") if isinstance(payload, list) else payload.get("generated_text", "")
    raise RuntimeError(f"Unsupported model provider: {provider}")


def generate_questions(model: dict[str, Any], subject: str, grade: str, count: int, school_state: str = "", school_district: str = "", topic: str = "", student_name: str = "", temperature: float = 0.3, include_visuals: bool = False) -> tuple[list[dict[str, Any]], str]:
    mistakes = historical_mistakes(student_name, grade, subject, topic) if student_name else []
    district_context = f" The student is in {school_state}, United States, and attends {school_district}. Align with this district's publicly available curriculum." if school_district else ""
    topic_context = f" The requested topic is {topic}." if topic else ""
    mistake_context = f" Prior incorrect questions to target are {mistakes}. Test the same skills with new wording, numbers, or contexts." if mistakes else ""
    visual_context = " Visual references are allowed for some questions when useful." if include_visuals else " Do not refer to pictures, diagrams, charts, maps, images, or anything the student cannot see. Every question must be answerable from text alone."
    question_subject = topic if subject == "Others" and topic else subject
    prompt = f"Create exactly {count} multiple-choice questions for {grade} students in {question_subject}.{topic_context}{district_context}{mistake_context}{visual_context} Questions must be unique within this exam. Vary recall, application, reasoning, vocabulary, and real-world contexts. Return only a JSON array with no markdown. Each item must have question, options (exactly four strings), and answer (one option string)."
    last_error = "unknown response"
    for _ in range(3):
        try:
            text = _request_text(model, prompt, temperature, max(800, count * 180))
            start, end = text.find("["), text.rfind("]")
            if start < 0 or end <= start:
                last_error = "response was not a JSON array"
                continue
            parsed = json.loads(text[start:end + 1])
            valid = unique_questions([item for item in parsed if isinstance(item, dict) and len(item.get("options", [])) == 4 and item.get("answer") in item.get("options", [])], count)
            if len(valid) == count:
                return valid, model["name"]
            last_error = f"received {len(valid)} unique valid questions"
        except requests.ConnectionError as error:
            raise RuntimeError(f"Could not reach {model['name']}. Check your internet connection.") from error
        except (ValueError, KeyError, TypeError, requests.RequestException, json.JSONDecodeError) as error:
            last_error = str(error)
    raise RuntimeError(f"{model['name']} could not create {count} unique questions after 3 attempts ({last_error}).")
