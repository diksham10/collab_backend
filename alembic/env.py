import asyncio
from logging.config import fileConfig
from typing import Optional

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel

from alembic import context

# Import all your models here so Alembic can see them
from src.auth.models import Users
from src.brand.models import BrandProfile
from src.influencer.models import InfluencerProfile
from src.event.models import Event, EventApplication
from src.chat.models import Message
from src.notification.models import Notification
from src.ratings.models import Rating
from src.admin_logs.models import AdminLog
from src.otp.models import OtpModel
from src.refresh_token.model import RefreshTokenModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# SQLModel metadata
target_metadata = SQLModel.metadata

# Read the database URL from alembic.ini
DATABASE_URL: Optional[str] = config.get_main_option("sqlalchemy.url")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations in 'online' mode with async engine."""
    connectable: AsyncEngine = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    """Helper function for running migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
