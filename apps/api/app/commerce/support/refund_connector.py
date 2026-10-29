"""Connect the existing refund operation runtime to the transactional mock provider."""

from sqlalchemy import text

from app.commerce.core.errors import MallError
from app.commerce.core.idempotency import execute
from app.commerce.order.refunds import RefundService
from app.commerce.order.schemas import RefundRequest
from app.services.agent.gateway.capabilities import CapabilitySpec
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import LedgerStore
from app.services.agent.gateway.idempotency import args_hash


class MallRefundConnector:
    def __init__(self, sessions, task):
        self.sessions, self.task = sessions, task

    async def submit(self, call):
        async with self.sessions() as db:
            if db.bind.dialect.name == "sqlite":
                await db.execute(text("BEGIN IMMEDIATE"))
            await self._authorized(db, call)
            payload = RefundRequest.model_validate({key: value for key, value in call.arguments.items()
                                                     if key in RefundRequest.model_fields})

            async def request():
                result = await RefundService(db).request(self.task.scope.customer_id,
                    order_id=call.arguments["order_id"], payload=payload,
                    key=args_hash({"user_id": self.task.scope.customer_id, "key": call.key}))
                return {"status": "ok", "order_id": result["order_id"], "refund_id": result["id"],
                        "refund_status": result["status"], "data_source": "mall_database", "gateway": "mock"}

            result = await execute(db, scope="refund.connector:" + self.task.scope.customer_id,
                                   key=call.key, arguments=call.arguments, action=request)
            await db.commit()
            return result

    async def status(self, call):
        async with self.sessions() as db:
            row = await RefundService(db).order_status(self.task.scope.customer_id, call.arguments["order_id"])
            state = (row or {}).get("status", "not_requested")
            return {"status": "ok", "order_id": call.arguments["order_id"],
                    "refund_id": (row or {}).get("id"), "refund_status": "refunded" if state == "settled" else state,
                    "data_source": "mall_database", "gateway": "mock"}

    async def _authorized(self, db, call):
        key = ActionGateway(LedgerStore()).key_for(scope_id=self.task.task_id, step=call.key,
            capability=CapabilitySpec(name="refund.submit"), args=call.arguments)
        entry = await LedgerStore().current(key, db=db)
        if self.task.assurance_level < 2 or entry is None:
            raise MallError("refund_intent_required", status=403)
        if entry.customer_id != self.task.scope.customer_id or entry.status != "INTENT":
            raise MallError("refund_intent_required", status=403)
