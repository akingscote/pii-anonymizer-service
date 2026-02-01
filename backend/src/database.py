"""Database configuration and session management."""

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Default database path - can be overridden via environment variable
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "pii_anonymizer.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite with FastAPI
    echo=False,  # Set to True for SQL debugging
)


# Enable WAL mode for better concurrent read performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for performance."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()


def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions outside FastAPI."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    # Ensure data directory exists
    db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Import models to register them with Base
    from backend.src.models import (  # noqa: F401
        AnonymizationConfig,
        AuditLog,
        EntityTypeConfig,
        PIIMapping,
    )

    Base.metadata.create_all(bind=engine)

    # Run migrations for existing databases
    _run_migrations()


def _run_migrations():
    """Run database migrations for schema updates."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Migration 1: Add last_used column to pii_mappings
        result = conn.execute(text("PRAGMA table_info(pii_mappings)"))
        columns = [row[1] for row in result.fetchall()]

        if "last_used" not in columns:
            # Add last_used column with default value from first_seen
            conn.execute(
                text("ALTER TABLE pii_mappings ADD COLUMN last_used DATETIME")
            )
            conn.execute(
                text("UPDATE pii_mappings SET last_used = first_seen WHERE last_used IS NULL")
            )
            conn.commit()

            # Create index for last_used
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_last_used ON pii_mappings (last_used)")
            )
            conn.commit()

        # Migration 2: Add locale column to anonymization_configs
        result = conn.execute(text("PRAGMA table_info(anonymization_configs)"))
        config_columns = [row[1] for row in result.fetchall()]

        if "locale" not in config_columns:
            conn.execute(
                text("ALTER TABLE anonymization_configs ADD COLUMN locale VARCHAR(10) DEFAULT 'en_US'")
            )
            conn.execute(
                text("UPDATE anonymization_configs SET locale = 'en_US' WHERE locale IS NULL")
            )
            conn.commit()

        # Migration 3: Add STREET_ADDRESS entity type to existing configs
        result = conn.execute(
            text("SELECT id FROM anonymization_configs WHERE is_active = 1")
        )
        active_configs = result.fetchall()

        for (config_id,) in active_configs:
            # Check if STREET_ADDRESS already exists for this config
            exists = conn.execute(
                text(
                    "SELECT 1 FROM entity_type_configs "
                    "WHERE config_id = :config_id AND entity_type = 'STREET_ADDRESS'"
                ),
                {"config_id": config_id},
            ).fetchone()

            if not exists:
                conn.execute(
                    text(
                        "INSERT INTO entity_type_configs "
                        "(config_id, entity_type, enabled, strategy) "
                        "VALUES (:config_id, 'STREET_ADDRESS', 1, 'replace')"
                    ),
                    {"config_id": config_id},
                )
        conn.commit()
