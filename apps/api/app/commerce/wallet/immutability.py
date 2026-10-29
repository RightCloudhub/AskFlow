"""ORM guard for dev/test; migrations also install database triggers."""

from sqlalchemy import event

from app.commerce.wallet.models import JournalEntry, Posting


def reject_mutation(_mapper, _connection, _target):
    raise ValueError("Financial entries are append-only; use a reversing journal")


def install():
    for model in (JournalEntry, Posting):
        for operation in ("before_update", "before_delete"):
            if not event.contains(model, operation, reject_mutation):
                event.listen(model, operation, reject_mutation)
