#!/usr/bin/env python3
"""Check hard code metrics (docs/engineering/code-metrics.md).

Limits:
  - function body lines (non-blank) <= 50
  - file physical lines <= 300
  - control nesting depth <= 3
  - positional params (excl self/cls) <= 3
  - cyclomatic complexity per function <= 10
  - magic numbers forbidden (named constants required)

Scope: apps/, packages/, evals/runners/, scripts/ (excl venv/node_modules/dist/__pycache__)
"""

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MAX_FUNC_LINES = 50
MAX_FILE_LINES = 300
MAX_NESTING = 3
MAX_POS_PARAMS = 3
MAX_COMPLEXITY = 10

SCAN_ROOTS = ("apps", "packages", "evals/runners", "scripts")
SKIP_PARTS = {
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "__pycache__",
    ".git",
    "site-packages",
}
PY_EXTS = {".py"}
TS_EXTS = {".ts", ".tsx"}
# §3 exceptions for magic numbers
ALLOWED_NUMBERS = {0, 1, -1, 2}


@dataclass
class Finding:
    metric: str
    path: str
    detail: str
    value: int | float | str
    limit: int | float | str
    line: int = 0


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    py_files: int = 0
    ts_files: int = 0

    def add(self, f: Finding) -> None:
        self.findings.append(f)


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def iter_source_files() -> list[Path]:
    out: list[Path] = []
    for rel in SCAN_ROOTS:
        base = ROOT / rel
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or is_skipped(p):
                continue
            if p.suffix in PY_EXTS | TS_EXTS:
                out.append(p)
    return sorted(out)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def count_physical_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def nonblank_lines_in_range(source_lines: list[str], start: int, end: int) -> int:
    """1-indexed inclusive line range; count non-blank lines."""
    n = 0
    for i in range(start - 1, min(end, len(source_lines))):
        if source_lines[i].strip():
            n += 1
    return n


def positional_param_count(args: ast.arguments) -> int:
    """Count positional-or-keyword params excluding self/cls; *args/**kwargs excluded."""
    names: list[str] = []
    for a in args.posonlyargs + args.args:
        names.append(a.arg)
    # drop self/cls only if first
    if names and names[0] in {"self", "cls"}:
        names = names[1:]
    return len(names)


class ComplexityVisitor(ast.NodeVisitor):
    """McCabe-like: +1 base, +1 per branch / boolean op / comprehension / except."""

    def __init__(self) -> None:
        self.score = 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return  # nested functions scored separately

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_If(self, node: ast.If) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.score += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.score += 1
        self.score += len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.score += max(0, len(node.cases) - 1)
        self.generic_visit(node)


CONTROL_TYPES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.Match,
    ast.IfExp,
)


def max_nesting_depth(node: ast.AST) -> int:
    """Max control-structure nesting inside function body (function itself = 0)."""

    def walk(n: ast.AST, depth: int) -> int:
        best = depth
        for child in ast.iter_child_nodes(n):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # nested defs: reset nesting for their body separately; still scan
                best = max(best, walk(child, 0))
                continue
            if isinstance(child, CONTROL_TYPES):
                best = max(best, walk(child, depth + 1))
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                best = max(best, walk(child, depth + 1))
            else:
                best = max(best, walk(child, depth))
        return best

    return walk(node, 0)


def is_module_or_class_assign_target(node: ast.AST, parents: list[ast.AST]) -> bool:
    """True if Constant is RHS of module/class level Assign/AnnAssign (named constant)."""
    if not parents:
        return False
    parent = parents[-1]
    if isinstance(parent, (ast.Assign, ast.AnnAssign)):
        # only treat as constant def if enclosing is Module or ClassDef
        for p in reversed(parents[:-1]):
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            if isinstance(p, (ast.Module, ast.ClassDef)):
                return True
        return isinstance(parents[0], ast.Module) if parents else False
    return False


def is_in_type_annotation(parents: list[ast.AST]) -> bool:
    for p in parents:
        if isinstance(p, ast.arg) and p.annotation is not None:
            pass
    # walk: if any parent is annotation field — hard with plain parents stack
    return False


class PyChecker(ast.NodeVisitor):
    def __init__(self, path: Path, source: str, report: Report) -> None:
        self.path = path
        self.source_lines = source.splitlines()
        self.report = report
        self.parents: list[ast.AST] = []
        self._func_stack: list[ast.AST] = []

    def generic_visit(self, node: ast.AST) -> None:
        self.parents.append(node)
        super().generic_visit(node)
        self.parents.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self._func_stack.append(node)
        self.generic_visit(node)
        self._func_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self._func_stack.append(node)
        self.generic_visit(node)
        self._func_stack.pop()

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        rpath = rel(self.path)
        name = node.name
        lineno = node.lineno
        end = node.end_lineno or lineno

        # function length: non-blank lines from def line through end
        flen = nonblank_lines_in_range(self.source_lines, lineno, end)
        if flen > MAX_FUNC_LINES:
            self.report.add(
                Finding(
                    "function_length",
                    rpath,
                    f"{name}()",
                    flen,
                    MAX_FUNC_LINES,
                    lineno,
                )
            )

        # positional params
        nparams = positional_param_count(node.args)
        if nparams > MAX_POS_PARAMS:
            self.report.add(
                Finding(
                    "positional_params",
                    rpath,
                    f"{name}() has {nparams} positional params",
                    nparams,
                    MAX_POS_PARAMS,
                    lineno,
                )
            )

        # nesting
        nest = max_nesting_depth(node)
        if nest > MAX_NESTING:
            self.report.add(
                Finding(
                    "nesting_depth",
                    rpath,
                    f"{name}() max nesting {nest}",
                    nest,
                    MAX_NESTING,
                    lineno,
                )
            )

        # complexity
        cv = ComplexityVisitor()
        for child in node.body:
            cv.visit(child)
        if cv.score > MAX_COMPLEXITY:
            self.report.add(
                Finding(
                    "cyclomatic_complexity",
                    rpath,
                    f"{name}() complexity {cv.score}",
                    cv.score,
                    MAX_COMPLEXITY,
                    lineno,
                )
            )

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, (int, float)):
            return
        if isinstance(node.value, bool):  # bool is int subclass
            return
        if node.value in ALLOWED_NUMBERS:
            return
        # allow floats that are effectively 0/1?
        if isinstance(node.value, float) and node.value in {0.0, 1.0, -1.0, 2.0}:
            return

        # skip if defining a module/class constant
        if self._is_constant_definition(node):
            return

        # skip annotations
        if self._in_annotation(node):
            return

        # only flag inside functions (body use)
        if not self._func_stack:
            return

        rpath = rel(self.path)
        func = self._func_stack[-1]
        fname = getattr(func, "name", "?")
        self.report.add(
            Finding(
                "magic_number",
                rpath,
                f"{fname}() uses magic number {node.value!r}",
                node.value,
                "named constant",
                node.lineno,
            )
        )

    def _is_constant_definition(self, node: ast.Constant) -> bool:
        """RHS of Assign/AnnAssign at module or class body."""
        if len(self.parents) < 1:
            return False
        # parents[-1] is current being visited — actually parent is parents[-1] before append?
        # In visit_Constant, parents already includes ... we append in generic_visit.
        # visit_Constant is called from generic_visit of parent, so parents ends with parent of Constant.
        parent = self.parents[-1] if self.parents else None
        if not isinstance(parent, (ast.Assign, ast.AnnAssign)):
            # BinOp etc. inside constant def still magic if inside function
            # Check if any Assign ancestor at class/module
            for i, p in enumerate(self.parents):
                if isinstance(p, (ast.Assign, ast.AnnAssign)):
                    # check if this assign is under FunctionDef
                    for q in self.parents[:i]:
                        if isinstance(q, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            return False
                    return True
            return False
        for p in self.parents:
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
        return True

    def _in_annotation(self, node: ast.Constant) -> bool:
        # Heuristic: parent chain includes AnnAssign annotation or arg.annotation
        for i, p in enumerate(self.parents):
            if isinstance(p, ast.AnnAssign) and p.annotation is not None:
                # constant might be inside annotation subtree
                if self._node_is_under(p.annotation, node):
                    return True
            if isinstance(p, ast.arg) and p.annotation is not None:
                if self._node_is_under(p.annotation, node):
                    return True
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)) and p.returns is not None:
                if self._node_is_under(p.returns, node):
                    return True
        return False

    def _node_is_under(self, root: ast.AST, target: ast.AST) -> bool:
        for n in ast.walk(root):
            if n is target:
                return True
        return False


def check_python(path: Path, report: Report) -> None:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        report.add(
            Finding("parse_error", rel(path), str(e), "error", "valid syntax", e.lineno or 0)
        )
        return
    PyChecker(path, source, report).visit(tree)


def check_ts_file_basics(path: Path, report: Report) -> None:
    """TS: file size only (no full AST without toolchain)."""
    # Function-level TS metrics need eslint; report file size only here
    pass


def main() -> int:
    report = Report()
    files = iter_source_files()
    report.files_scanned = len(files)

    for path in files:
        nlines = count_physical_lines(path)
        rpath = rel(path)
        if nlines > MAX_FILE_LINES:
            report.add(
                Finding("file_size", rpath, "physical lines", nlines, MAX_FILE_LINES, 1)
            )

        if path.suffix in PY_EXTS:
            report.py_files += 1
            check_python(path, report)
        else:
            report.ts_files += 1
            check_ts_file_basics(path, report)

    # Aggregate
    by_metric: dict[str, list[Finding]] = defaultdict(list)
    for f in report.findings:
        by_metric[f.metric].append(f)

    metric_order = [
        "file_size",
        "function_length",
        "nesting_depth",
        "positional_params",
        "cyclomatic_complexity",
        "magic_number",
        "parse_error",
    ]

    print("=" * 72)
    print("AskFlow code metrics audit")
    print(f"Root: {ROOT}")
    print(f"Limits: func≤{MAX_FUNC_LINES} file≤{MAX_FILE_LINES} nest≤{MAX_NESTING} "
          f"params≤{MAX_POS_PARAMS} cc≤{MAX_COMPLEXITY} no magic nums")
    print(f"Scanned: {report.files_scanned} files "
          f"(py={report.py_files}, ts/tsx={report.ts_files})")
    print("Note: TS/TSX only checked for file_size (no local eslint AST).")
    print("=" * 72)

    total = 0
    summary_rows: list[tuple[str, int]] = []
    for metric in metric_order:
        items = by_metric.get(metric, [])
        summary_rows.append((metric, len(items)))
        total += len(items)

    print("\n## Summary\n")
    print(f"| metric | violations |")
    print(f"|--------|----------:|")
    for m, c in summary_rows:
        print(f"| {m} | {c} |")
    print(f"| **TOTAL** | **{total}** |")

    # Top offenders per metric
    for metric in metric_order:
        items = by_metric.get(metric, [])
        if not items:
            continue
        print(f"\n## {metric} ({len(items)})\n")
        # sort by severity (value desc when numeric)
        def sort_key(x: Finding):
            v = x.value
            if isinstance(v, (int, float)):
                return (-float(v), x.path, x.line)
            return (0, x.path, x.line)

        items_sorted = sorted(items, key=sort_key)
        show = items_sorted if len(items_sorted) <= 40 else items_sorted[:40]
        for f in show:
            loc = f"{f.path}:{f.line}" if f.line else f.path
            print(f"  - {loc}  {f.detail}  → {f.value} (limit {f.limit})")
        if len(items_sorted) > 40:
            print(f"  ... and {len(items_sorted) - 40} more")

    # File-level hotspots (files with most findings)
    by_file: dict[str, int] = defaultdict(int)
    for f in report.findings:
        by_file[f.path] += 1
    if by_file:
        print("\n## Top files by violation count\n")
        top = sorted(by_file.items(), key=lambda x: -x[1])[:25]
        for path, n in top:
            print(f"  {n:4d}  {path}")

    # JSON sidecar for tooling
    out_json = ROOT / "docs" / "engineering" / "code-metrics-report.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "limits": {
            "function_length": MAX_FUNC_LINES,
            "file_size": MAX_FILE_LINES,
            "nesting_depth": MAX_NESTING,
            "positional_params": MAX_POS_PARAMS,
            "cyclomatic_complexity": MAX_COMPLEXITY,
        },
        "files_scanned": report.files_scanned,
        "total_violations": total,
        "by_metric": {m: c for m, c in summary_rows},
        "findings": [
            {
                "metric": f.metric,
                "path": f.path,
                "line": f.line,
                "detail": f.detail,
                "value": f.value if not isinstance(f.value, float) else f.value,
                "limit": f.limit,
            }
            for f in report.findings
        ],
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nJSON report: {out_json.relative_to(ROOT)}")

    # Pass if zero violations
    if total == 0:
        print("\nRESULT: PASS (0 violations)")
        return 0
    print(f"\nRESULT: FAIL ({total} violations)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
