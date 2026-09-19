"""Database schema updates for multi-student and Google authentication support."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    MetaData,
    Table,
)
from datetime import datetime

metadata = MetaData()

# Parents table - stores parent account information
parents = Table(
    "parents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("parent_name", Text, nullable=False),
    Column("username", Text, nullable=False, unique=True),
    Column("email", Text, nullable=False, unique=True),
    Column("password_hash", Text, nullable=True),  # Nullable for Google users
    Column("google_id", Text, nullable=True),  # Google OAuth ID
    Column("auth_type", Text, nullable=False, default="manual"),  # 'manual' or 'google'
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

# Students table - stores student information linked to parents
students = Table(
    "students",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("student_id", Text, nullable=False, unique=True),  # External student ID
    Column("student_name", Text, nullable=False),
    Column("parent_id", Integer, ForeignKey("parents.id"), nullable=False),
    Column("grade", Text, nullable=False),
    Column("country", Text, nullable=False),
    Column("school_state", Text, nullable=False, server_default=""),
    Column("school_district", Text, nullable=False, server_default=""),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

# OTP codes table - for password reset functionality
otp_codes = Table(
    "otp_codes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("parent_id", Integer, ForeignKey("parents.id"), nullable=False),
    Column("code", Text, nullable=False),
    Column("expires_at", Text, nullable=False),
    Column("used", Boolean, nullable=False, default=False),
    Column("created_at", Text, nullable=False),
)

# Email queue table - for managing email sending
email_queue = Table(
    "email_queue",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("to_email", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("status", Text, nullable=False, default="pending"),  # 'pending', 'sent', 'failed'
    Column("created_at", Text, nullable=False),
    Column("sent_at", Text, nullable=True),
    Column("error_message", Text, nullable=True),
)

# Migration SQL for new tables
MIGRATION_SQL = """
-- Create parents table
CREATE TABLE IF NOT EXISTS parents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    google_id TEXT,
    auth_type TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Create students table
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL UNIQUE,
    student_name TEXT NOT NULL,
    parent_id INTEGER NOT NULL,
    grade TEXT NOT NULL,
    country TEXT NOT NULL,
    school_state TEXT NOT NULL DEFAULT '',
    school_district TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES parents(id)
);

-- Create otp_codes table
CREATE TABLE IF NOT EXISTS otp_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES parents(id)
);

-- Create email_queue table
CREATE TABLE IF NOT EXISTS email_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    sent_at TEXT,
    error_message TEXT
);

-- Add student_id to exams table if it doesn't exist
ALTER TABLE exams ADD COLUMN student_id INTEGER;
ALTER TABLE exams ADD COLUMN parent_id INTEGER;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_students_parent_id ON students(parent_id);
CREATE INDEX IF NOT EXISTS idx_exams_student_id ON exams(student_id);
CREATE INDEX IF NOT EXISTS idx_exams_parent_id ON exams(parent_id);
CREATE INDEX IF NOT EXISTS idx_otp_codes_parent_id ON otp_codes(parent_id);
CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
"""

def get_migration_sql() -> str:
    """Return the SQL migration script."""
    return MIGRATION_SQL