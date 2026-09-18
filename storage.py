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

# Columns added after the first release. Databases created by an older version are
# upgraded in place because SQLite and PostgreSQL share this ADD COLUMN syntax.
EXAM_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("school_district", "TEXT NOT NULL DEFAULT ''"),
    ("school_state", "TEXT NOT NULL DEFAULT ''"),
    ("topic", "TEXT NOT NULL DEFAULT ''"),
    ("question_set_id", "INTEGER"),
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
                    question_set_id INTEGER
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
            
            _upgrade_exam_columns(None)  # Pass None since we're using HTTP client directly
        else:
            engine = get_engine()
            metadata.create_all(engine)
            _upgrade_exam_columns(engine)
        
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


def execute(sql: str, params: Mapping[str, Any] | None = None) -> int | None:
    """Run a write statement.

    Returns the first column of the first returned row when the statement ends
    with ``RETURNING`` (used to read a new row's ``id``), otherwise ``None``.
    """
    ensure_schema()
    
    if is_turso():
        # Convert named parameters to positional for Turso HTTP API
        import re
        param_names = re.findall(r':(\w+)', sql)
        sql_str = re.sub(r':\w+', '?', sql)
        param_list = [params.get(name) for name in param_names] if params else []
        
        result = _turso_execute(sql_str, param_list)
        
        # Check if this is a RETURNING query
        if "RETURNING" in sql.upper():
            if result and result.get("results") and result["results"][0].get("rows"):
                return int(result["results"][0]["rows"][0][0]) if result["results"][0]["rows"][0][0] is not None else None
        return None
    
    with get_engine().begin() as connection:
        result = connection.execute(text(sql), dict(params or {}))
        if not result.returns_rows:
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
