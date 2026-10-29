"""Capture actual row mutations in the command transaction, including bulk SQL.

This infrastructure observes writes already authorized by domain services; it
does not perform cross-domain business queries or change statement results.
"""

from sqlalchemy import and_, event, inspect, select

IGNORED_TABLES = frozenset({"audit_logs", "outbox", "idempotency_records"})


def serializable(row):
    from datetime import datetime

    from app.commerce.core.schemas import utc

    return {key: utc(value).isoformat() if isinstance(value, datetime) else value
            for key, value in dict(row).items()}


def primary_filter(table, values):
    return and_(*(column == values[column.name] for column in table.primary_key))


class Changes:
    def __init__(self, db):
        self.session = db.sync_session
        self.rows, self.pending = {}, []

    def __enter__(self):
        self.session.info["mall_changes"] = self
        event.listen(self.session, "do_orm_execute", self.execute, retval=True)
        event.listen(self.session, "before_flush", self.before_flush)
        event.listen(self.session, "after_flush_postexec", self.after_flush)
        return self

    def __exit__(self, *_args):
        self.session.info.pop("mall_changes", None)
        event.remove(self.session, "do_orm_execute", self.execute)
        event.remove(self.session, "before_flush", self.before_flush)
        event.remove(self.session, "after_flush_postexec", self.after_flush)

    def remember(self, table, before, after):
        identity = after or before
        if identity is None:
            return
        key = (table.name, tuple(identity[column.name] for column in table.primary_key))
        original = self.rows.get(key, {}).get("before", before)
        self.rows[key] = {"table": table.name, "before": original, "after": after}

    def execute(self, state):
        if not (state.is_update or state.is_delete):
            return state.invoke_statement()
        table = state.statement.table
        if table.name in IGNORED_TABLES:
            return state.invoke_statement()
        connection = self.session.connection()
        query = select(table)
        if state.statement.whereclause is not None:
            query = query.where(state.statement.whereclause)
        before = list(connection.execute(query, state.parameters or {}).mappings())
        result = state.invoke_statement()
        for row in before:
            after = connection.execute(select(table).where(primary_filter(table, row))).mappings().first()
            self.remember(table, serializable(row), serializable(after) if after else None)
        return result

    def before_flush(self, session, _context, _instances):
        objects = set(session.new) | set(session.dirty) | set(session.deleted)
        self.pending = []
        for obj in objects:
            table = inspect(obj).mapper.local_table
            if table.name in IGNORED_TABLES:
                continue
            before = self.read_object(obj) if obj not in session.new else None
            self.pending.append((obj, before))

    def after_flush(self, _session, _context):
        for obj, before in self.pending:
            table = inspect(obj).mapper.local_table
            self.remember(table, before, self.read_object(obj))
        self.pending = []

    def read_object(self, obj):
        table = inspect(obj).mapper.local_table
        values = {column.name: getattr(obj, column.name) for column in table.primary_key}
        row = self.session.connection().execute(select(table).where(primary_filter(table, values))).mappings().first()
        return serializable(row) if row else None

    def detail(self):
        return list(self.rows.values())
