"""Middleware package for authentication and other cross-cutting concerns."""

from middleware.auth.auth_middleware import (
    get_current_parent,
    get_current_student,
    is_parent_authenticated,
    logout_parent,
    require_parent_auth,
    require_profile_access,
    require_student_selection,
    set_current_student,
    with_parent_auth,
)

__all__ = [
    "get_current_parent",
    "get_current_student",
    "is_parent_authenticated",
    "logout_parent",
    "require_parent_auth",
    "require_profile_access",
    "require_student_selection",
    "set_current_student",
    "with_parent_auth",
]