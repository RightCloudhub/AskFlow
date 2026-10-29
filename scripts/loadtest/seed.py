"""Seed a disposable benchmark DB and write local credentials with mode 0600."""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.commerce.account.sessions import issue_session
from app.commerce.catalog.models import Sku, SkuPrice, Spu
from app.commerce.inventory.models import FlashSale, FlashSaleSku, Inventory
from app.commerce.infra.runtime import infra
from app.commerce.wallet.service import WalletService
from app.core import database
from app.core.config import get_settings
from app.models.user import User
from app.plugins.loader import load_plugins

DEFAULT_USERS = 200
STOCK = 1000000
PRICE_CENTS = 100
BALANCE_CENTS = 100000
SALE_HOURS = 2
OUTPUT_MODE = 0o600


async def products(db):
    product = Spu(title="Load test product", status="active")
    db.add(product)
    await db.flush()
    sku = Sku(spu_id=product.id, title=product.title, code="load-" + uuid4().hex, status="active")
    db.add(sku)
    await db.flush()
    now = datetime.now(UTC)
    sale = FlashSale(name="Load test flash", starts_at=now, ends_at=now + timedelta(hours=SALE_HOURS))
    db.add_all([SkuPrice(sku_id=sku.id, original_cents=PRICE_CENTS, sale_cents=PRICE_CENTS, valid_from=now),
                Inventory(sku_id=sku.id, available=STOCK), sale])
    await db.flush()
    offer = FlashSaleSku(sale_id=sale.id, sku_id=sku.id, stock=STOCK, price_cents=PRICE_CENTS)
    db.add(offer)
    await db.flush()
    return {"spu_id": product.id, "sku_id": sku.id, "sale_id": sale.id, "offer_id": offer.id}


async def accounts(db, count):
    results = []
    for _index in range(count):
        user = User(username="load_" + uuid4().hex, email=uuid4().hex + "@example.com", hashed_password="!load-only")
        db.add(user)
        await db.flush()
        await WalletService(db).credit(user.id, BALANCE_CENTS, key="load:" + user.id, source="adjustment")
        results.append({"user_id": user.id, **await issue_session(db, user, device="loadtest")})
    return results


async def seed(count):
    settings = get_settings()
    if settings.is_production_like:
        raise ValueError("Load seeding requires a disposable development/test database")
    load_plugins(settings)
    async with database.SessionLocal() as db:
        fixture = await products(db)
        fixture["users"] = await accounts(db, count)
        await db.commit()
    if settings.flash_sale_backend == "redis":
        await infra().redis.client().set("mall:flash:" + fixture["offer_id"], STOCK)
    await infra().close()
    await database.engine.dispose()
    return fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--output", default="artifacts/mall-seed.json")
    args = parser.parse_args()
    if args.users < 1:
        parser.error("--users must be positive")
    data = asyncio.run(seed(args.users))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode=OUTPUT_MODE)
    with os.fdopen(descriptor, "w") as output:
        os.fchmod(output.fileno(), OUTPUT_MODE)
        json.dump(data, output)
    print("Load fixture written; contains credentials, do not upload or commit")


if __name__ == "__main__":
    main()
