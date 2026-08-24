import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Enum, String, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base
from app.models import Category, Listing  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata

EXTERNAL_POSTGRES_COLUMNS = {
    ("listings", "embedding"),
    ("listings", "search_document"),
}
EXTERNAL_POSTGRES_INDEXES = {
    "ix_listings_embedding_hnsw",
    "ix_listings_search_document",
}


def include_object(object_, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    if reflected and compare_to is None:
        if type_ == "column" and (object_.table.name, name) in EXTERNAL_POSTGRES_COLUMNS:
            return False
        if type_ == "index" and name in EXTERNAL_POSTGRES_INDEXES:
            return False
    return True


def compare_column_type(  # type: ignore[no-untyped-def]
    context_, inspected_column, metadata_column, inspected_type, metadata_type
):
    # Migrations intentionally use portable VARCHAR columns for Python StrEnum values.
    if isinstance(metadata_type, Enum) and isinstance(inspected_type, String):
        return False
    return None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=compare_column_type,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=compare_column_type,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
