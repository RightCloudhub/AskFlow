"""Domain-local worker entry points share the caller transaction."""

from sqlalchemy import select

from app.commerce.core.errors import MallError


async def verification(db, row):
    from app.commerce.account.delivery import deliver

    await deliver(db, row)


async def expiry(db, row):
    from app.commerce.order.service import OrderService

    await OrderService(db).cancel(row.user_id, row.id)


async def refund(db, row):
    from app.commerce.order.refunds import RefundService

    await RefundService(db).process(row.id)


async def payment(db, row):
    from app.commerce.payment.compensation import compensate

    await compensate(db, row.id)


async def reward(db, row):
    from app.commerce.referral.service import ReferralService

    await ReferralService(db).mature(row.id)


async def notification(db, row):
    from app.commerce.notify.delivery import deliver

    await deliver(db, row)


async def flash(db, row):
    from app.commerce.inventory.flash import fulfill

    try:
        async with db.begin_nested():
            await fulfill(db, row)
    except MallError as exc:
        await db.refresh(row)
        row.status, row.error_code = "rejected", exc.code


async def dispatch(db, job, *, resource_id: str):
    from app.commerce.job_registry import model_for

    model = model_for(job)
    statement = select(model).where(model.id == resource_id)
    if job.name in {"verification", "notification", "flash"}:
        statement = statement.with_for_update()
    row = await db.scalar(statement.execution_options(populate_existing=True))
    if row is None or getattr(row, job.state_column) not in job.states:
        return
    handlers = {"verification": verification, "expiry": expiry, "refund": refund,
                "payment": payment, "reward": reward, "notification": notification, "flash": flash}
    await handlers[job.name](db, row)
