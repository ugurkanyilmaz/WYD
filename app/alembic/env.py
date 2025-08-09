from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base
config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata
def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix='sqlalchemy.')
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
if context.is_offline_mode():
    raise RuntimeError('offline migrations not supported in this example')
else:
    run_migrations_online()
