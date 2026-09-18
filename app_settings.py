from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


def read_setting(name: str) -> str | None:
    """Return a configured value from Streamlit secrets first, then the environment.

    Locally the value comes from ``.env``; on Streamlit Community Cloud the same
    value is pasted into the app's *Advanced settings -> Secrets* box, which is
    exposed through ``st.secrets``. Secrets are matched case-insensitively
    because provider keys are named in upper case (``GROQ_API_KEY``) while the
    Parent Results credentials were historically written in lower case
    (``parent_username``). Lookups never raise: a missing or malformed
    secrets.toml simply means the value is not configured.
    """
    if not name:
        return None
    for candidate in (name, name.lower()):
        try:
            value = st.secrets.get(candidate)
        except Exception:  # noqa: BLE001 - secrets.toml may be absent or unreadable
            value = None
        if value:
            return str(value)
    for candidate in (name, name.upper(), name.lower()):
        value = os.getenv(candidate)
        if value:
            return value
    return None
