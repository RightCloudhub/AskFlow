"""Production never bootstraps schema with create_all."""

from sqlalchemy import text

from app.core import database

MALL_SCHEMA_REVISION = "20261029_mall_v1"


async def prepare_schema(settings):
    if not settings.is_production_like:
        await database.init_db()
        if settings.commerce_enabled():
            from app.migrations.mall_v1.integrity import install

            async with database.engine.begin() as connection:
                await connection.run_sync(install)
        return
    async with database.engine.connect() as connection:
        await connection.execute(text("SELECT 1 FROM users LIMIT 1"))
        if settings.commerce_enabled():
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != MALL_SCHEMA_REVISION:
                raise RuntimeError("Commerce schema is not current; run the migration job first")
