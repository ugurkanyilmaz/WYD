from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 🔧 PYTHONPATH'e proje klasörünü ekliyoruz (önemli!)
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 📦 Ayarları ve modelleri import ediyoruz
from app.core.config import settings
from app.core.database import Base
from app.models import user  # diğer modeller geldikçe buraya da eklenmeli

# 🔧 Alembic config
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 🔧 Logger ayarları (logları .ini'den alıyor)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 🔧 Alembic’in metadata’sı – model bilgilerini buradan alır
target_metadata = Base.metadata

# 🔽 Offline migration – veritabanına bağlanmadan SQL scripti oluşturmak için
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

# 🔽 Online migration – veritabanına bağlanıp direkt tabloyu yaratmak için
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# 🔄 Migration modunu seç
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
