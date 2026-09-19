"""Data storage for Study Sprint.

Three backends are supported and the choice is automatic:

* **No ``DATABASE_URL`` configured** — a local SQLite file (``education_app.db``).
  This is the development default and keeps every existing script working.
* **``DATABASE_URL`` configured with libsql://** — Turso (SQLite Flash) database.
  The URL is read from the environment or from Streamlit secrets. Turso provides
  a managed SQLite database with cloud persistence and edge caching.
* **``DATABASE_URL`` configured with postgresql://** — that hosted database is used instead. The
  URL is read from the environment or from Streamlit secrets, so a Neon,
  Supabase, CockroachDB, Aiven or Railway PostgreSQL database can be attached
  without a code change.

Streamlit Community Cloud does not guarantee the persistence of local file
storage, so ``education_app.db`` inside a deployed container can disappear at any
time. Point ``DATABASE_URL`` at a hosted Turso or PostgreSQL database to keep saved
results across hibernations and redeploys.

All SQL in this app is written once, with named bind parameters (``:name``), and
runs on all backends; SQLAlchemy's ``Table`` metadata generates the correct
primary-key definition (``AUTOINCREMENT`` versus ``IDENTITY``) for each dialect.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Mapping
from urllib.parse import urlsplit

import requests

from sqlalchemy import (
    Column,
    Engine,
    Integer,
    MetaData,
    Table,
    Text,
    Boolean,
    ForeignKey,
    create_engine,
    event,
    inspect,
    text,
)

from app_settings import BASE_DIR, read_setting

try:
    from libsql_client import create_client
    TURSO_AVAILABLE = True
except ImportError:
    TURSO_AVAILABLE = False

DEFAULT_SQLITE_PATH = BASE_DIR / "education_app.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

metadata = MetaData()

exams = Table(
    "exams",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("student_name", Text, nullable=False),
    Column("grade", Text, nullable=False),
    Column("country", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("question_count", Integer, nullable=False),
    Column("time_limit", Integer, nullable=False),
    Column("start_time", Text, nullable=False),
    Column("end_time", Text, nullable=False),
    Column("score", Integer, nullable=False),
    Column("correct_count", Integer, nullable=False),
    Column("wrong_count", Integer, nullable=False),
    Column("questions_json", Text, nullable=False),
    Column("school_state", Text, nullable=False, server_default=""),
    Column("school_district", Text, nullable=False, server_default=""),
    Column("topic", Text, nullable=False, server_default=""),
        Column("question_set_id", Integer),
    Column("student_id", Text, nullable=True),  # Public student id (e.g. "STU-001")
    Column("parent_id", Integer, nullable=True),   # New column for parent reference
)

question_sets = Table(
    "question_sets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("student_name", Text, nullable=False),
    Column("grade", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("topic", Text, nullable=False),
    Column("questions_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)

# New tables for multi-student and authentication support
parents = Table(
    "parents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("parent_name", Text, nullable=False),
    Column("username", Text, nullable=False, unique=True),
    Column("email", Text, nullable=False, unique=True),
    Column("password_hash", Text, nullable=True),
    Column("google_id", Text, nullable=True),
    Column("auth_type", Text, nullable=False, default="manual"),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

students = Table(
    "students",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("student_id", Text, nullable=False, unique=True),
    Column("student_name", Text, nullable=False),
    Column("parent_id", Integer, ForeignKey("parents.id"), nullable=False),
    Column("grade", Text, nullable=False),
    Column("country", Text, nullable=False),
    Column("school_state", Text, nullable=False, server_default=""),
    Column("school_district", Text, nullable=False, server_default=""),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

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

email_queue = Table(
    "email_queue",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("to_email", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("status", Text, nullable=False, default="pending"),
    Column("created_at", Text, nullable=False),
    Column("sent_at", Text, nullable=True),
    Column("error_message", Text, nullable=True),
)

# Columns added after the first release. Databases created by an older version are
# upgraded in place because SQLite and PostgreSQL share this ADD COLUMN syntax.
EXAM_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("school_district", "TEXT NOT NULL DEFAULT ''"),
    ("school_state", "TEXT NOT NULL DEFAULT ''"),
    ("topic", "TEXT NOT NULL DEFAULT ''"),
        ("question_set_id", "INTEGER"),
    ("student_id", "TEXT"),
    ("parent_id", "INTEGER"),
)

_lock = threading.RLock()
_engine: Engine | None = None
_schema_ready = False


def database_url() -> str:
    """The configured database URL, or the local SQLite file when none is set."""
    return (read_setting("DATABASE_URL") or "").strip() or DEFAULT_DATABASE_URL


def _normalized_url(url: str) -> str:
    """Route database URLs through the appropriate drivers.

    - ``postgres://`` and ``postgresql://`` URLs go through psycopg 3 driver
    - ``libsql://`` URLs are for Turso (SQLite Flash) and use libsql-client
    - ``sqlite://`` URLs use the default SQLite driver

    Hosted providers hand out URLs like ``postgresql://user:pw@host/db`` which
    SQLAlchemy otherwise resolves to psycopg2. Rewriting the scheme keeps the
    pasted URL working with the driver this project installs.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def is_turso() -> bool:
    """True when the configured database is Turso (libsql://)."""
    return database_url().startswith("libsql")


def is_hosted() -> bool:
    """True when results are stored outside the app container."""
    return not database_url().startswith("sqlite")


def backend_label() -> str:
    """A short description of the active backend that never exposes credentials."""
    url = database_url()
    if url.startswith("sqlite"):
        return f"local SQLite file ({DEFAULT_SQLITE_PATH.name})"
    parts = urlsplit(url)
    database = parts.path.lstrip("/") or "database"
    return f"hosted {parts.scheme.split('+')[0]} database '{database}' at {parts.hostname}"


def _configure_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
    """Let concurrent Streamlit sessions share one SQLite file safely."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def _get_turso_http_client() -> tuple[str, str]:
    """Return Turso HTTP endpoint and auth token for direct HTTP requests."""
    url = database_url()
    if not url.startswith("libsql://"):
        raise RuntimeError(f"DATABASE_URL must start with libsql:// for Turso, got: {url}")
    
    parsed = urlsplit(url)
    
    # Extract auth token from URL
    auth_token = parsed.username or ""
    
    # Convert libsql:// to https:// for HTTP requests
    # Format: https://hostname/path
    http_url = f"https://{parsed.hostname}{parsed.path}"
    
    return http_url, auth_token


def _turso_execute(sql: str, params: list[Any] | None = None) -> Any:
    """Execute SQL query using Turso HTTP API."""
    http_url, auth_token = _get_turso_http_client()
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Use parameters directly if provided
    sql_str = sql
    param_list = params if params else []
    
    payload = {
        "statements": [
            {
                "q": sql_str,
                "params": param_list
            }
        ]
    }
    
    response = requests.post(http_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    
    # Handle different response formats from Turso
    if isinstance(result, list):
        # Turso returns a list of statement results
        if len(result) > 0 and result[0].get("error"):
                        raise RuntimeError(f"Turso query error: {result[0]['error']}")
        # Extract the actual results from the first statement
        if len(result) > 0 and result[0].get("results"):
            return {"results": [result[0]["results"]]}
        return {"results": result}
    elif isinstance(result, dict):
        if result.get("results") and result["results"][0].get("error"):
            raise RuntimeError(f"Turso query error: {result['results'][0]['error']}")
        return result
    
    return result


def _turso_execute_statements(statements: list[dict[str, Any]]) -> Any:
    """Execute several statements in one Turso HTTP request.

    All statements run on the same server-side connection, so a statement like
    ``SELECT last_insert_rowid()`` can read the row written by a preceding
    ``INSERT`` in the same batch. ``_turso_execute`` exists for single-statement
    calls; this helper keeps multi-statement work in one round-trip.
    """
    http_url, auth_token = _get_turso_http_client()

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(http_url, headers=headers, json={"statements": statements}, timeout=30)
    response.raise_for_status()

    result = response.json()

    # Normalise the various Turso response shapes to {"results": [...]}.
    if isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict) and entry.get("error"):
                raise RuntimeError(f"Turso query error: {entry['error']}")
        return {"results": result}
    if isinstance(result, dict):
        return result
    return result


def _extract_turso_scalar(result: Any) -> int | None:
    """Return the first cell of the first row of a Turso response, or None.

    Used to read the id returned by the batched ``SELECT last_insert_rowid()``.
    Walks the ``{"results": [{"rows": [[...]]}]}`` structure without assuming a
    single exact shape, since the HTTP API has changed its envelope over time.
    """
    if not isinstance(result, dict):
        return None
    results = result.get("results")
    if not isinstance(results, list):
        return None
    for entry in results:
        if not isinstance(entry, dict):
            continue
        rows = entry.get("rows")
        if rows and isinstance(rows, list) and rows[0] and len(rows[0]) > 0:
            value = rows[0][0]
            if value is not None:
                return int(value)
    return None


def get_engine() -> Engine | None:
    """Return the process-wide engine, creating it on first use. Returns None for Turso."""
    global _engine
    with _lock:
        if _engine is None:
            url = _normalized_url(database_url())
            if url.startswith("sqlite"):
                engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)
                event.listen(engine, "connect", _configure_sqlite)
                _engine = engine
            elif url.startswith("libsql"):
                # For Turso, we don't use SQLAlchemy engine - we use libsql-client directly
                # Return None to indicate we're using the Turso client
                return None
            else:
                # pool_pre_ping recovers connections that a hosted/serverless
                # database closed while the app was idle.
                engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, future=True)
                _engine = engine
        return _engine


def _upgrade_exam_columns(engine: Engine | None = None) -> None:
    """Add columns that were introduced after a database was first created."""
    if is_turso():
        # For Turso, we need to handle schema upgrades differently
        try:
            result = _turso_execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exams'")
            if not result or not result.get("results") or not result["results"][0].get("rows"):
                return
            
            # Get existing columns
            result = _turso_execute("PRAGMA table_info(exams)")
            existing = set()
            if result and result.get("results") and result["results"][0].get("rows"):
                for row in result["results"][0]["rows"]:
                    if len(row) > 1:
                        existing.add(row[1])  # row[1] is the column name
            
            for name, definition in EXAM_COLUMN_MIGRATIONS:
                if name in existing:
                    continue
                _turso_execute(f"ALTER TABLE exams ADD COLUMN {name} {definition}")
        except Exception as e:
            # If upgrade fails, we'll try again on next run
            print(f"Turso column upgrade failed: {e}")
            pass
        return
    
    if engine is None:
        return
    
    inspector = inspect(engine)
    if not inspector.has_table("exams"):
        return
    existing = {column["name"] for column in inspector.get_columns("exams")}
    for name, definition in EXAM_COLUMN_MIGRATIONS:
        if name in existing:
            continue
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE exams ADD COLUMN {name} {definition}"))


def ensure_schema() -> None:
    """Create the tables and upgrade old databases. Runs once per process."""
    global _schema_ready
    if _schema_ready:
        return
    
    with _lock:
        if _schema_ready:
            return
        
        if is_turso():
            # Create tables using raw SQL for Turso via HTTP API
            _turso_execute("""
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    country TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    question_count INTEGER NOT NULL,
                    time_limit INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    correct_count INTEGER NOT NULL,
                    wrong_count INTEGER NOT NULL,
                    questions_json TEXT NOT NULL,
                    school_state TEXT NOT NULL DEFAULT '',
                    school_district TEXT NOT NULL DEFAULT '',
                    topic TEXT NOT NULL DEFAULT '',
                                        question_set_id INTEGER,
                    student_id TEXT,
                    parent_id INTEGER
                )
            """)
            
            _turso_execute("""
                CREATE TABLE IF NOT EXISTS question_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    questions_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create new tables for multi-student support
            _turso_execute("""
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
                )
            """)
            
            _turso_execute("""
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
                )
            """)
            
            _turso_execute("""
                CREATE TABLE IF NOT EXISTS otp_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (parent_id) REFERENCES parents(id)
                )
            """)
            
            _turso_execute("""
                CREATE TABLE IF NOT EXISTS email_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    to_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    error_message TEXT
                )
            """)
            
            _upgrade_exam_columns(None)  # Pass None since we're using HTTP client directly
        else:
            engine = get_engine()
            metadata.create_all(engine)
            _upgrade_exam_columns(engine)
            
            # Create indexes for new tables
            with engine.begin() as connection:
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_students_parent_id ON students(parent_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_exams_student_id ON exams(student_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_exams_parent_id ON exams(parent_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_otp_codes_parent_id ON otp_codes(parent_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status)"))
        
        _schema_ready = True


def fetch_all(sql: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a read statement and return the rows as plain dictionaries."""
    ensure_schema()
    
    if is_turso():
        # Convert named parameters to positional for Turso HTTP API
        import re
        param_names = re.findall(r':(\w+)', sql)
        sql_str = re.sub(r':\w+', '?', sql)
        param_list = [params.get(name) for name in param_names] if params else []
        
        result = _turso_execute(sql_str, param_list)
        
        # Convert Turso HTTP result to list of dicts
        if result and result.get("results") and result["results"][0].get("rows"):
            columns = result["results"][0].get("columns", [])
            rows = result["results"][0]["rows"]
            return [dict(zip(columns, row)) for row in rows]
        else:
            return []
    
    with get_engine().connect() as connection:
        result = connection.execute(text(sql), dict(params or {}))
        return [dict(row._mapping) for row in result]


def fetch_one(sql: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Run a read statement and return the first row as a dictionary, or None."""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Mapping[str, Any] | None = None) -> int | None:
    """Run a write statement.

    When the statement is an ``INSERT``, the new row's ``id`` is returned;
    otherwise ``None``. The id is obtained in the *same* round-trip as the write
    so it works on every backend. This matters on the stateless Turso HTTP API,
    where a later ``SELECT last_insert_rowid()`` would run on a different
    connection and always return 0.
    """
    ensure_schema()

    params = dict(params or {})
    is_insert = sql.lstrip().upper().startswith("INSERT")

    if is_turso():
        # Convert named parameters to positional for the Turso HTTP API.
        import re
        param_names = re.findall(r':(\w+)', sql)
        sql_str = re.sub(r':\w+', '?', sql)
        param_list = [params.get(name) for name in param_names]

        if is_insert:
            # Batch the INSERT and the id lookup into one request so
            # last_insert_rowid() runs on the same connection as the write.
            statements = [
                {"q": sql_str, "params": param_list},
                {"q": "SELECT last_insert_rowid()", "params": []},
            ]
            result = _turso_execute_statements(statements)
            return _extract_turso_scalar(result)

        _turso_execute(sql_str, param_list)
        return None

    with get_engine().begin() as connection:
        if is_insert and get_engine().dialect.name == "postgresql":
            # PostgreSQL has no last_insert_rowid(); RETURNING id is the
            # reliable way to read the new key on the shared connection.
            result = connection.execute(text(f"{sql} RETURNING id"), params)
            row = result.first()
            return int(row[0]) if row is not None and row[0] is not None else None

        result = connection.execute(text(sql), params)
        if not result.returns_rows:
            if is_insert:
                # SQLite exposes the rowid of the just-inserted row on the same
                # connection used for the write.
                row = connection.execute(text("SELECT last_insert_rowid()")).first()
                return int(row[0]) if row is not None and row[0] is not None else None
            return None
        row = result.first()
        return int(row[0]) if row is not None else None


def existing_columns(table: str) -> set[str]:
    """Names of the columns currently present in ``table``."""
    ensure_schema()
    
    if is_turso():
        try:
            result = _turso_execute(f"PRAGMA table_info({table})")
            if result and result.get("results") and result["results"][0].get("rows"):
                return {row[1] for row in result["results"][0]["rows"] if len(row) > 1}  # row[1] is the column name
        except Exception:
            return set()
        return set()
    
    engine = get_engine()
    if engine is None:
        return set()
    
    inspector = inspect(engine)
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def has_saved_results() -> bool:
    """True when at least one completed exam has been stored."""
    return bool(fetch_all("SELECT id FROM exams LIMIT 1"))
