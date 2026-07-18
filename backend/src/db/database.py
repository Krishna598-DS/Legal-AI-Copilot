"""SQLAlchemy engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import get_settings

settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_add_column(table: str, column: str, ddl: str) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        existing = {r[1] for r in rows}
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            conn.commit()


def migrate_sqlite() -> None:
    """Best-effort additive migrations for existing SQLite DBs."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    try:
        _sqlite_add_column("users", "email_verified", "email_verified BOOLEAN DEFAULT 0")
        _sqlite_add_column("users", "terms_version", "terms_version VARCHAR(50)")
        _sqlite_add_column("users", "privacy_version", "privacy_version VARCHAR(50)")
        _sqlite_add_column("users", "google_sub", "google_sub VARCHAR(255)")
        _sqlite_add_column("users", "stripe_customer_id", "stripe_customer_id VARCHAR(255)")
        _sqlite_add_column("users", "plan", "plan VARCHAR(50) DEFAULT 'free'")
        _sqlite_add_column("users", "org_id", "org_id VARCHAR(36)")
        _sqlite_add_column("users", "org_role", "org_role VARCHAR(50)")
        _sqlite_add_column(
            "users", "role", "role VARCHAR(50) DEFAULT 'individual'"
        )
        _sqlite_add_column("documents", "page_count", "page_count INTEGER DEFAULT 0")
        _sqlite_add_column("documents", "has_tables", "has_tables BOOLEAN DEFAULT 0")
        _sqlite_add_column(
            "documents", "processing_error", "processing_error TEXT"
        )
        _sqlite_add_column("chat_messages", "sources_json", "sources_json TEXT")
        # Backfill persona for any NULL legacy rows
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE users SET role = 'individual' "
                    "WHERE role IS NULL OR role = ''"
                )
            )
            conn.commit()
    except Exception:
        pass


def init_db() -> None:
    """Create tables and required directories."""
    import os

    from src.db import models  # noqa: F401

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.INDEX_DIR, exist_ok=True)
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    migrate_sqlite()
