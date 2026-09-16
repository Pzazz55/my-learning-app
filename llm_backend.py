from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
MODELS_PATH = BASE_DIR / "models.json"
load_dotenv(BASE_DIR / ".env")


def load_models() -> list[dict[str, Any]]:
    with MODELS_PATH.open(encoding="utf-8") as file:
        models = json.load(file)
    available = []
    for model in models:
        if not model.get("enabled", True):
            continue
        key_name = model.get("api_key_env", "")
        try:
            key = st.secrets.get(key_name) or os.getenv(key_name)
        except Exception:
            key = os.getenv(key_name)
        if key:
            available.append(model)
    return available


def unique_questions(questions: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for question in questions:
        key = " ".join(str(question.get("question", "")).lower().split())
        if key and key not in seen:
            seen.add(key)
            unique.append(question)
    return unique[:count]


def historical_mistakes(db_path: Path, student_name: str, grade: str, subject: str, topic: str) -> list[str]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT questions_json FROM exams WHERE lower(student_name) = lower(?) AND grade = ? AND subject = ? AND topic = ? ORDER BY end_time DESC",
        (student_name, grade, subject, topic),
    ).fetchall()
    connection.close()
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
    try:
        key = st.secrets.get(key_name) or os.getenv(key_name)
    except Exception:
        key = os.getenv(key_name)
    if not key:
        raise RuntimeError(f"Missing API key. Add {key_name} to .env for {model['name']}.")
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


def generate_questions(db_path: Path, model: dict[str, Any], subject: str, grade: str, count: int, school_state: str = "", school_district: str = "", topic: str = "", student_name: str = "", temperature: float = 0.3, include_visuals: bool = False) -> tuple[list[dict[str, Any]], str]:
    mistakes = historical_mistakes(db_path, student_name, grade, subject, topic) if student_name else []
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
