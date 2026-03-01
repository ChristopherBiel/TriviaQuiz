from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.storage.postgres import Base, _build_url  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def _get_url() -> str:
    url = _build_url()
    return str(url)


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_build_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
