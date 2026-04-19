from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from app.config import get_settings
from app.database import Base
from app.models.user import User
from app.models.research import ResearchSession, ResearchFinding, ResearchAnswer, LLMPreference

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.sync_db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from alembic import environmentcontext
    connectable = pool.create_pooled_connection(context.config)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
