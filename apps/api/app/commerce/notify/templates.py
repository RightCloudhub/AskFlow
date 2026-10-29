"""Plain-text templates interpolate explicit scalar event fields, never expressions."""

import re

FIELDS = frozenset({"order_id", "refund_id", "payment_id", "journal_id", "ticket_id",
                    "status", "amount_cents", "total_cents", "currency", "run_id", "differences"})
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def render(template: str, payload: dict):
    def replace(match):
        name = match.group(1)
        value = payload.get(name, "")
        return str(value) if name in FIELDS and type(value) in {str, int} else ""

    return PLACEHOLDER.sub(replace, template)
