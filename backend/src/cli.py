"""CLI for database initialization and management."""

import argparse
import sys

from backend.src.database import init_db, get_db_context
from backend.src.models import AnonymizationConfig, EntityTypeConfig


# Default entity types to enable
DEFAULT_ENTITY_TYPES = [
    ("PERSON", "replace", None),
    ("EMAIL_ADDRESS", "replace", None),
    ("PHONE_NUMBER", "replace", None),
    ("CREDIT_CARD", "replace", None),
    ("US_SSN", "replace", None),
    ("IP_ADDRESS", "replace", None),
    ("LOCATION", "replace", None),
    ("STREET_ADDRESS", "replace", None),
    ("DATE_TIME", "replace", None),
    ("GUID", "replace", None),
]


def seed_default_config():
    """Seed the database with a default configuration."""
    with get_db_context() as db:
        # Check if a config already exists
        existing = db.query(AnonymizationConfig).filter_by(is_active=True).first()
        if existing:
            print(f"Active configuration already exists: {existing.name}")
            return

        # Create default config
        config = AnonymizationConfig(
            name="default",
            is_active=True,
            confidence_threshold=0.7,
            language="en",
            locale="en_US",
        )
        db.add(config)
        db.flush()  # Get the config ID

        # Add entity type configurations
        for entity_type, strategy, params in DEFAULT_ENTITY_TYPES:
            entity_config = EntityTypeConfig(
                config_id=config.id,
                entity_type=entity_type,
                enabled=True,
                strategy=strategy,
                strategy_params=params,
            )
            db.add(entity_config)

        print(f"Created default configuration with {len(DEFAULT_ENTITY_TYPES)} entity types")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="PII Anonymizer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init-db command
    init_parser = subparsers.add_parser("init-db", help="Initialize the database")
    init_parser.add_argument(
        "--seed", action="store_true", help="Also seed with default configuration"
    )

    # seed-config command
    subparsers.add_parser("seed-config", help="Seed default configuration")

    args = parser.parse_args()

    if args.command == "init-db":
        print("Initializing database...")
        init_db()
        print("Database initialized successfully")
        if args.seed:
            seed_default_config()

    elif args.command == "seed-config":
        print("Seeding default configuration...")
        seed_default_config()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
