from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from streamlit.testing.v1 import AppTest

CONFIG_PATH = Path("config/config.json") if Path("config/config.json").exists() else Path("config.json")
DEFAULT_CONFIG = {"timezone": "America/New_York", "timezone_label": "Eastern Time"}
TEST_STUDENT = "__cline_verify__"


def write_config(payload: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def report(at: AppTest, note: str) -> None:
    print(f"{note}: exceptions={len(at.exception)}")
    for error in at.exception:
        print("  EXC:", error.value[:600])


def clock_parts(at: AppTest) -> tuple[str | None, str | None]:
    for markdown in at.markdown:
        markup = str(markdown.value)
        if "clock-zone" in markup:
            found_time = re.search(r'class="clock-time">([^<]+)<', markup)
            found_zone = re.search(r'class="clock-zone">([^<]+)<', markup)
            return (found_time.group(1) if found_time else None, found_zone.group(1) if found_zone else None)
    return (None, None)


def sidebars(at: AppTest, kind: str) -> list[str]:
    try:
        return [str(getattr(item, "value")) for item in getattr(at.sidebar, kind)]
    except Exception as error:  # noqa: BLE001 - probe helper
        return [f"<{kind} unavailable: {error}>"]


def stub_generate(db_path, model, subject, grade, count, school_state="", school_district="", topic="", student_name="", temperature=0.3, include_visuals=False):
    questions = [
        {"question": f"Verify {index} about {topic}?", "options": ["Alpha", "Beta", "Gamma", "Delta"], "answer": "Alpha"}
        for index in range(count)
    ]
    return questions, "stub-model"


print("=== 1. Default config.json (America/New_York) drives the clock ===")
write_config(DEFAULT_CONFIG)
at = AppTest.from_file("learning-home.py", default_timeout=60)
at.run()
report(at, "learning-home")
clock_time, clock_zone = clock_parts(at)
print(f"  clock        : {clock_time} | {clock_zone}")
expected = datetime.now(ZoneInfo("America/New_York"))
print(f"  expected     : {expected.strftime('%I:%M:%S %p').lstrip('0')} | {expected.strftime('%Z')} · Eastern Time")
print("  sidebar note :", [text for text in sidebars(at, "caption") if "Clock" in text])

print()
print("=== 2. Switching config.json to Asia/Kolkata moves the clock ===")
write_config({"timezone": "Asia/Kolkata", "timezone_label": "India Standard Time"})
at = AppTest.from_file("learning-home.py", default_timeout=60)
at.run()
report(at, "learning-home")
clock_time, clock_zone = clock_parts(at)
print(f"  clock        : {clock_time} | {clock_zone}")
expected = datetime.now(ZoneInfo("Asia/Kolkata"))
print(f"  expected     : {expected.strftime('%I:%M:%S %p').lstrip('0')} | {expected.strftime('%Z')} · India Standard Time")
print("  sidebar note :", [text for text in sidebars(at, "caption") if "Clock" in text])

print()
print("=== 3. An invalid timezone falls back instead of crashing ===")
write_config({"timezone": "Mars/Olympus", "timezone_label": "Olympus Time"})
at = AppTest.from_file("learning-home.py", default_timeout=60)
at.run()
report(at, "learning-home")
clock_time, clock_zone = clock_parts(at)
print(f"  clock        : {clock_time} | {clock_zone}")
print()
print("=== 4. Exam header shows name, grade, subject and topic ===")
write_config(DEFAULT_CONFIG)
import llm_backend

llm_backend.generate_questions = stub_generate
at = AppTest.from_file("learning-home.py", default_timeout=60)
at.run()
boxes = {box.label: box for box in at.selectbox}
boxes["Subject"].select("Science")
at.run()
boxes = {box.label: box for box in at.selectbox}
boxes["Topic"].select("Weather & Seasons")
at.run()
for widget in at.text_input:
    if widget.label == "Student name":
        widget.set_value(TEST_STUDENT)
at.run()
[button for button in at.button if "Start exam" in str(button.label)][0].click().run()
report(at, "learning-home exam screen")
pill = next((str(markdown.value) for markdown in at.markdown if 'class="pill"' in str(markdown.value)), "<no pill>")
print("  pill:", pill)
from html import escape
for label, needle in (("name", TEST_STUDENT), ("grade", "Grade 1"), ("subject", "Science"), ("topic", "Weather & Seasons")):
    print(f"  contains {label:<7}:", escape(needle) in pill)
clock_time, clock_zone = clock_parts(at)
print(f"  exam clock   : {clock_time} | {clock_zone}")

print()
print("=== 5. Parent review shows options and a readable grade ===")
at.session_state["exam"]["deadline"] = 0
at.run()
report(at, "after expiring the timer (exam saved to SQLite)")

parent = AppTest.from_file("pages/parent-results.py", default_timeout=60)
parent.session_state["parent_authenticated"] = True
parent.run()
report(parent, "parent-results")
tables = [str(markdown.value) for markdown in parent.markdown if "results-table" in str(markdown.value)]
print("  review tables:", len(tables))
if tables:
    table = tables[-1]
    print("  header           :", table[: table.find("</thead>") + 8])
    print("  row 1            :", table[table.find("<tbody>") : table.find("<tbody>") + 300])
    print("  has Options column:", "<th>Options</th>" in table)
    print("  has A)/B) options :", "A) Alpha" in table and "B) Beta" in table and "D) Delta" in table)
metrics = [(metric.label, metric.value) for metric in parent.metric]
print("  grade metric:", [item for item in metrics if item[0] == "Grade"])
print("  all metrics :", metrics[:6])
print("  completed   :", [str(caption.value) for caption in parent.caption if "Completed" in str(caption.value)][:1])

connection = sqlite3.connect("education_app.db")
connection.execute("DELETE FROM exams WHERE student_name = ?", (TEST_STUDENT,))
connection.execute("DELETE FROM question_sets WHERE student_name = ?", (TEST_STUDENT,))
connection.commit()
left = connection.execute("SELECT COUNT(*) FROM exams WHERE student_name = ?", (TEST_STUDENT,)).fetchone()[0]
connection.close()
print("  verification rows cleaned up, remaining:", left)

print()
print("=== 6. Restore the default config.json ===")
write_config(DEFAULT_CONFIG)
print("  ", CONFIG_PATH.read_text(encoding="utf-8").strip().replace("\n", " "))
