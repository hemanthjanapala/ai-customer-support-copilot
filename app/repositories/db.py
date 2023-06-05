"""Database helpers.

Phase 1: only used for the health check probe.
Phase 2: SQLAlchemy engine + session + table models (see ARCHITECTURE.md section 8).
"""

from sqlalchemy import create_engine, text

from app.config import settings


def check_database() -> str:
    if not settings.database_url:
        return "not_configured"
    try:
        kwargs: dict = {}
        if settings.database_url.startswith("postgresql"):
            kwargs = {"connect_args": {"connect_timeout": 2}}
        engine = create_engine(settings.database_url, **kwargs)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unreachable"
