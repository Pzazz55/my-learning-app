"""Authentication middleware for parent access control."""

from __future__ import annotations

import hmac
from typing import Callable, Any

import streamlit as st

from app_settings import read_setting
from backend.services.logging_config import get_logger

logger = get_logger(__name__)


def require_parent_auth() -> None:
    """Require parent authentication for access to protected pages.
    
    This middleware checks if the user is authenticated as a parent.
    If not, it redirects to the app entry point, which shows the login screen.
    """
    if not st.session_state.get("parent_authenticated", False):
        st.warning("Please log in to access this page.")
        st.switch_page("learning-home.py")


def is_parent_authenticated() -> bool:
    """Check if the current session is authenticated as a parent."""
    return st.session_state.get("parent_authenticated", False)


def get_current_parent() -> dict[str, Any] | None:
    """Get the current authenticated parent data."""
    return st.session_state.get("parent_data")


def logout_parent() -> None:
    """Log out the current parent session."""
    parent = st.session_state.get("parent_data") or {}
    logger.info("Parent '%s' signed out.", parent.get("username"))
    st.session_state.parent_authenticated = False
    st.session_state.parent_data = None
    st.session_state.current_student_id = None
    st.rerun()


def with_parent_auth(func: Callable) -> Callable:
    """Decorator to require parent authentication for a function.
    
    Usage:
        @with_parent_auth
        def my_protected_function():
            # This will only run if parent is authenticated
            pass
    """
    def wrapper(*args, **kwargs):
        require_parent_auth()
        return func(*args, **kwargs)
    return wrapper


def require_profile_access() -> None:
    """Require security check for profile access.
    
    This middleware ensures proper authentication before allowing profile access.
    For manual accounts: requires username/password verification.
    For Google accounts: requires re-authentication.
    """
    if not is_parent_authenticated():
        st.switch_page("learning-home.py")
    
    parent = get_current_parent()
    if not parent:
        st.error("Parent session expired. Please log in again.")
        logout_parent()
    
    # Check if profile access has been verified in this session
    if not st.session_state.get("profile_access_verified", False):
        st.markdown("## Security Verification")
        st.caption("Please verify your identity to access profile settings")
        
        auth_type = parent.get("auth_type", "manual")
        
        if auth_type == "google":
            st.info("You are using Google authentication. Please re-authenticate to continue.")
            if st.button("Re-authenticate with Google", type="primary"):
                # Store the current page for redirect after auth
                st.session_state.redirect_after_auth = "profile"
                st.switch_page("pages/parent-login.py")
        else:
            with st.form("profile_security_check"):
                username = st.text_input("Parent Username")
                password = st.text_input("Parent Password", type="password")
                submitted = st.form_submit_button("Verify", type="primary")
            
            if submitted:
                from backend.services.auth_storage import verify_parent_credentials
                verified_parent = verify_parent_credentials(username, password)
                
                if verified_parent and verified_parent["id"] == parent["id"]:
                    st.session_state.profile_access_verified = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.stop()


def set_current_student(student_id: str) -> None:
    """Set the current student for the session."""
    st.session_state.current_student_id = student_id


def get_current_student() -> str | None:
    """Get the current student ID for the session."""
    return st.session_state.get("current_student_id")


def require_student_selection() -> None:
    """Require that a student is selected for multi-student views."""
    if not get_current_student():
        st.warning("Please select a student to view their data.")
        st.stop()