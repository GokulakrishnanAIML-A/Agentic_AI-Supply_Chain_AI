from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401  ensure models are registered

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    # Auto-migrate HITL lifecycle columns for existing databases
    _hitl_migrations = [
        "ALTER TABLE decision_runs ADD COLUMN IF NOT EXISTS hitl_status VARCHAR(32) DEFAULT 'PENDING_REVIEW'",
        "ALTER TABLE decision_runs ADD COLUMN IF NOT EXISTS hitl_reviewed_by VARCHAR(128)",
        "ALTER TABLE decision_runs ADD COLUMN IF NOT EXISTS hitl_reviewed_at TIMESTAMP",
        "ALTER TABLE decision_runs ADD COLUMN IF NOT EXISTS hitl_comments TEXT",
    ]
    with engine.connect() as conn:
        for stmt in _hitl_migrations:
            conn.execute(text(stmt))
        conn.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
