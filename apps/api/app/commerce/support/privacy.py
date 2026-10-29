"""Support snapshots contain no retained customer contact data after closure."""

from sqlalchemy import update

from app.commerce.support.models import SupportLink


async def anonymize(db, user_id: str):
    await db.execute(update(SupportLink).where(SupportLink.user_id == user_id).values(snapshot={}))
