"""Shared appearance (Light/Dark) toggle.

The same toggle renders on every page and is backed by one session-state key,
so the choice a user makes on one screen is honoured on every other screen
until they change it again. Pages call :func:`render_appearance_toggle` and
then apply the returned theme with ``inject_styles`` / ``inject_parent_theme``.
"""

from __future__ import annotations

import streamlit as st

APPEARANCE_KEY = "appearance_theme"
THEME_LIGHT = "Light"
THEME_DARK = "Dark"
THEME_OPTIONS = [THEME_LIGHT, THEME_DARK]


def render_appearance_toggle(default: str = THEME_DARK, container=None) -> str:
    """Render the Light/Dark picker once and return the active theme.

    Args:
        default: theme used the first time the picker is shown in a session.
        container: sidebar (default) or any other Streamlit container.

    The value lives in ``st.session_state['appearance_theme']`` so it survives
    Streamlit reruns and page switches. ``index`` is only a first-run default.
    """
    if APPEARANCE_KEY not in st.session_state or st.session_state.get(APPEARANCE_KEY) not in THEME_OPTIONS:
        st.session_state[APPEARANCE_KEY] = default if default in THEME_OPTIONS else THEME_DARK

    target = container if container is not None else st.sidebar
    theme = target.radio(
        "Appearance",
        THEME_OPTIONS,
        index=THEME_OPTIONS.index(st.session_state[APPEARANCE_KEY]),
        horizontal=True,
        key=APPEARANCE_KEY,
    )
    return theme
