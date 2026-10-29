"""Database setup and SQLAlchemy session helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "jewelrytryon.db"


def _resolve_database_url() -> tuple[str, Path | None]:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        if configured.startswith("sqlite:///"):
            raw_path = configured.removeprefix("sqlite:///")
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                db_path = ROOT_DIR / db_path
            return f"sqlite:///{db_path.as_posix()}", db_path
        return configured, None
    return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}", DEFAULT_DB_PATH


DATABASE_URL, DATABASE_PATH = _resolve_database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    """Base class for database models."""


def init_db() -> None:
    from app.models import Generation, Upload  # noqa: F401

    if DATABASE_PATH is not None:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
