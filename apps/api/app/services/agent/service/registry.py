"""Feasibility gate, separate from the agent's candidate ordering."""

from pydantic import ValidationError

from app.services.agent.service.contracts import Environment, Operation, OperationCall


class OperationRegistry:
    def __init__(self, operations: list[Operation]) -> None:
        self.operations = {op.operation_id: op for op in operations}
        if len(self.operations) != len(operations):
            raise ValueError("Duplicate operation identifier")

    def rejection(self, call: OperationCall, env: Environment) -> str | None:
        op = self.operations.get(call.operation_id)
        if op is None:
            return "unknown_operation"
        if op.operation_id not in env.available_operations:
            return "unavailable"
        if op.permission not in env.permissions:
            return "permission_denied"
        try:
            args = op.input_schema.model_validate(call.arguments, strict=True)
        except ValidationError:
            return "invalid_arguments"
        if not op.precondition(args, env):
            return "precondition_failed"
        return None
