"""Owned, encrypted delivery addresses exposed only through this service."""

from sqlalchemy import select, update

from app.commerce.account.crypto import decrypt, encrypt
from app.commerce.account.models import Address
from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas, owned, owned_page


def address_view(row):
    return {"id": row.id, "version": row.version, "name": decrypt(row.name_cipher),
            "phone": decrypt(row.phone_cipher), "address": decrypt(row.address_cipher),
            "is_default": row.is_default}


class AddressService:
    def __init__(self, db):
        self.db = db

    async def get(self, user_id: str, address_id: str):
        return await owned(self.db, Address, owner_id=user_id, resource_id=address_id)

    async def snapshot(self, user_id: str, address_id: str | None):
        if not address_id:
            return {}
        row = await self.get(user_id, address_id)
        return {"name_cipher": row.name_cipher, "phone_cipher": row.phone_cipher,
                "address_cipher": row.address_cipher}

    async def list(self, user_id: str, *, cursor: str = ""):
        rows, after = await owned_page(self.db, Address, owner_id=user_id, cursor=cursor)
        return {"items": [address_view(row) for row in rows], "next_cursor": after}

    async def save(self, user_id: str, payload, *, address_id: str | None = None):
        if payload.is_default:
            await self.db.execute(update(Address).where(Address.user_id == user_id).values(is_default=False))
        values = {"name_cipher": encrypt(payload.name), "phone_cipher": encrypt(payload.phone),
                  "address_cipher": encrypt(payload.address), "is_default": payload.is_default}
        if address_id:
            row = await self.get(user_id, address_id)
            if row.version != payload.expected_version:
                raise MallError("version_conflict")
            await cas(self.db, row, values=values)
        else:
            row = Address(user_id=user_id, **values)
            self.db.add(row)
            await self.db.flush()
        return address_view(row)

    async def anonymize(self, user_id: str):
        rows = await self.db.scalars(select(Address).where(Address.user_id == user_id))
        for row in rows:
            row.name_cipher, row.phone_cipher, row.address_cipher = encrypt("deleted"), "", encrypt("deleted")
