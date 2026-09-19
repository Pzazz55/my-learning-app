"""Authentication and user management storage functions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Mapping

from backend.services.storage import execute, fetch_all, fetch_one

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_parent(
    parent_name: str,
    username: str,
    email: str,
    password: str | None = None,
    google_id: str | None = None,
    auth_type: str = "manual"
) -> int:
    """Create a new parent account."""
    password_hash = hash_password(password) if password else None
    now = datetime.now(timezone.utc).isoformat()
    
    result = execute(
        """INSERT INTO parents (parent_name, username, email, password_hash, google_id, auth_type, created_at, updated_at)
           VALUES (:parent_name, :username, :email, :password_hash, :google_id, :auth_type, :created_at, :updated_at)
           RETURNING id""",
        {
            "parent_name": parent_name,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "google_id": google_id,
            "auth_type": auth_type,
            "created_at": now,
            "updated_at": now,
        }
    )
    return int(result or 0)

def get_parent_by_username(username: str) -> dict[str, Any] | None:
    """Get parent by username."""
    parents = fetch_all(
        "SELECT * FROM parents WHERE username = :username",
        {"username": username}
    )
    return parents[0] if parents else None

def get_parent_by_email(email: str) -> dict[str, Any] | None:
    """Get parent by email."""
    parents = fetch_all(
        "SELECT * FROM parents WHERE email = :email",
        {"email": email}
    )
    return parents[0] if parents else None

def get_parent_by_google_id(google_id: str) -> dict[str, Any] | None:
    """Get parent by Google ID."""
    parents = fetch_all(
        "SELECT * FROM parents WHERE google_id = :google_id",
        {"google_id": google_id}
    )
    return parents[0] if parents else None

def verify_parent_credentials(username: str, password: str) -> dict[str, Any] | None:
    """Verify parent credentials for manual authentication."""
    parent = get_parent_by_username(username)
    if not parent or parent.get("auth_type") != "manual":
        return None
    
    password_hash = hash_password(password)
    if parent.get("password_hash") == password_hash:
        return parent
    return None

def create_student(
    student_id: str,
    student_name: str,
    parent_id: int,
    grade: str,
    country: str,
    school_state: str = "",
    school_district: str = ""
) -> int:
    """Create a new student account."""
    now = datetime.now(timezone.utc).isoformat()
    
    result = execute(
        """INSERT INTO students (student_id, student_name, parent_id, grade, country, school_state, school_district, created_at, updated_at)
           VALUES (:student_id, :student_name, :parent_id, :grade, :country, :school_state, :school_district, :created_at, :updated_at)
           RETURNING id""",
        {
            "student_id": student_id,
            "student_name": student_name,
            "parent_id": parent_id,
            "grade": grade,
            "country": country,
            "school_state": school_state,
            "school_district": school_district,
            "created_at": now,
            "updated_at": now,
        }
    )
    return int(result or 0)

def get_students_by_parent(parent_id: int) -> list[dict[str, Any]]:
    """Get all students for a parent."""
    return fetch_all(
        "SELECT * FROM students WHERE parent_id = :parent_id ORDER BY created_at DESC",
        {"parent_id": parent_id}
    )

def delete_student(student_id: str, parent_id: int) -> bool:
    """Delete one of this parent's students.

    The ``parent_id`` predicate guarantees a parent can only ever remove a
    child that belongs to them.
    """
    execute(
        "DELETE FROM students WHERE student_id = :student_id AND parent_id = :parent_id",
        {"student_id": student_id, "parent_id": parent_id},
    )
    return True

def count_students_by_parent(parent_id: int) -> int:
    """Number of students linked to a parent."""
    rows = fetch_all(
        "SELECT COUNT(*) AS total FROM students WHERE parent_id = :parent_id",
        {"parent_id": parent_id},
    )
    return int(rows[0]["total"]) if rows else 0

def get_student_by_id(student_id: str) -> dict[str, Any] | None:
    """Get student by student_id."""
    students = fetch_all(
        "SELECT * FROM students WHERE student_id = :student_id",
        {"student_id": student_id}
    )
    return students[0] if students else None

def update_student(
    student_id: str,
    student_name: str | None = None,
    grade: str | None = None,
    country: str | None = None,
    school_state: str | None = None,
    school_district: str | None = None
) -> bool:
    """Update student information."""
    updates = []
    params = {"student_id": student_id}
    
    if student_name is not None:
        updates.append("student_name = :student_name")
        params["student_name"] = student_name
    if grade is not None:
        updates.append("grade = :grade")
        params["grade"] = grade
    if country is not None:
        updates.append("country = :country")
        params["country"] = country
    if school_state is not None:
        updates.append("school_state = :school_state")
        params["school_state"] = school_state
    if school_district is not None:
        updates.append("school_district = :school_district")
        params["school_district"] = school_district
    
    if not updates:
        return False
    
    updates.append("updated_at = :updated_at")
    params["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    sql = f"UPDATE students SET {', '.join(updates)} WHERE student_id = :student_id"
    execute(sql, params)
    return True

def generate_otp(parent_id: int, expiry_minutes: int = 15) -> str:
    """Generate and store an OTP code for password reset."""
    code = secrets.token_hex(3).upper()  # 6-character alphanumeric code
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    
    execute(
        """INSERT INTO otp_codes (parent_id, code, expires_at, used, created_at)
           VALUES (:parent_id, :code, :expires_at, 0, :created_at)""",
        {
            "parent_id": parent_id,
            "code": code,
            "expires_at": expires_at,
            "created_at": now,
        }
    )
    return code

def verify_otp(parent_id: int, code: str) -> bool:
    """Verify an OTP code and mark it as used."""
    otps = fetch_all(
        """SELECT * FROM otp_codes 
           WHERE parent_id = :parent_id AND code = :code AND used = 0 AND expires_at > :now""",
        {
            "parent_id": parent_id,
            "code": code,
            "now": datetime.now(timezone.utc).isoformat(),
        }
    )
    
    if not otps:
        return False
    
    otp_id = otps[0]["id"]
    execute("UPDATE otp_codes SET used = 1 WHERE id = :id", {"id": otp_id})
    return True

def update_parent_password(parent_id: int, new_password: str) -> bool:
    """Update parent password."""
    password_hash = hash_password(new_password)
    now = datetime.now(timezone.utc).isoformat()
    
    execute(
        """UPDATE parents SET password_hash = :password_hash, updated_at = :updated_at 
           WHERE id = :parent_id""",
        {
            "parent_id": parent_id,
            "password_hash": password_hash,
            "updated_at": now,
        }
    )
    return True

def queue_email(to_email: str, subject: str, body: str) -> int:
    """Add an email to the sending queue."""
    now = datetime.now(timezone.utc).isoformat()
    
    result = execute(
        """INSERT INTO email_queue (to_email, subject, body, status, created_at)
           VALUES (:to_email, :subject, :body, 'pending', :created_at)
           RETURNING id""",
        {
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "created_at": now,
        }
    )
    return int(result or 0)

def get_pending_emails() -> list[dict[str, Any]]:
    """Get all pending emails from the queue."""
    return fetch_all(
        "SELECT * FROM email_queue WHERE status = 'pending' ORDER BY created_at ASC"
    )

def mark_email_sent(email_id: int, error_message: str | None = None) -> bool:
    """Mark an email as sent or failed."""
    now = datetime.now(timezone.utc).isoformat()
    status = "failed" if error_message else "sent"
    
    execute(
        """UPDATE email_queue SET status = :status, sent_at = :sent_at, error_message = :error_message 
           WHERE id = :id""",
        {
            "id": email_id,
            "status": status,
            "sent_at": now,
            "error_message": error_message,
        }
    )
    return True

def link_exam_to_student_parent(exam_id: int, student_id: int, parent_id: int) -> bool:
    """Link an existing exam to a student and parent."""
    execute(
        """UPDATE exams SET student_id = :student_id, parent_id = :parent_id 
           WHERE id = :exam_id""",
        {
            "exam_id": exam_id,
            "student_id": student_id,
            "parent_id": parent_id,
        }
    )
    return True

def get_exams_by_parent(parent_id: int, student_id: int | None = None) -> list[dict[str, Any]]:
    """Get exams for a parent, optionally filtered by student."""
    if student_id:
        return fetch_all(
            """SELECT * FROM exams WHERE parent_id = :parent_id AND student_id = :student_id 
               ORDER BY end_time DESC""",
            {"parent_id": parent_id, "student_id": student_id}
        )
    return fetch_all(
        """SELECT * FROM exams WHERE parent_id = :parent_id ORDER BY end_time DESC""",
        {"parent_id": parent_id}
    )