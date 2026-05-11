#!/usr/bin/env python3
"""i18n guard (Phase 2 / Issue #106).

API レスポンス相当箇所と MCP の公開コード表面に日本語混入がないことを
fail-fast で検証する。Phase 1 完了時点で API/Pydantic は全て英語化済みなので、
本ガードは「リグレッション防止」が主目的。

検出範囲:
  1. `api/lib/routers/**/*.py` の `HTTPException(detail=...)` 等で
     `detail` キーワード引数に渡される文字列リテラル
  2. `api/lib/models/**/*.py` の Pydantic `Field(..., description=...)` で
     `description` キーワード引数に渡される文字列リテラル
  3. `api/lib/routers/**/*.py` の `JSONResponse(content=...)` 等の
     `content` キーワード引数 (dict 内の値文字列も再帰的に検査)
  4. `mcp/server.py` / `mcp/tools/**/*.py` / `mcp/errors.py` の全文字列
     リテラル (公開ツール記述全体が対象)

検出パターン: Hiragana (U+3040–U+309F) / Katakana (U+30A0–U+30FF) /
CJK 統合漢字 (U+4E00–U+9FFF) のいずれかが文字列リテラル中に含まれる場合。
`ast` モジュールで Python を構文解析するため、複数行にまたがる
`detail=(...)` や f-string、辞書のネスト、HTTPException / JSONResponse /
Response の特定位置 positional 引数にも対応する。

検出対象 / 非対象の境界:
  - **対象**: 上記 1-4 の文脈下にある `ast.Constant`(str) / `JoinedStr` /
    `BinOp` / `Dict` / `List` / `Tuple` 等の string ノード。
    MCP 側 (項目 4) は関数 docstring も含めて全文字列リテラルを検査する
    (公開 tool の I/O 説明として client に露出するため)。
  - **非対象**: Python のコメント (`# ...`) と **モジュールトップの
    docstring** (リポジトリ内部向けの説明として通常残置される)。
    spec 14 章「コードコメントの一括英語化はしない」を守る。

Usage:
  python3 .github/workflows/scripts/i18n_guard.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# Hiragana (U+3040–U+309F), Katakana (U+30A0–U+30FF + prolonged sound mark),
# CJK 統合漢字 (U+4E00–U+9FFF)。
JP_CHARS = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")


def iter_string_literals(node: ast.AST):
    """Recursively yield (lineno, value) for every string literal under `node`.

    `ast.walk` で部分木全体を走査し、`Constant(str)` を全て拾う。これにより
    `IfExp` (`'a' if cond else 'b'`)、`Subscript` (`{'k':'v'}['k']`)、
    comprehensions、ネストした dict/list、Call 内 args/kwargs 等を
    手書き分岐なしに網羅できる (Copilot PR #125 round 4 指摘)。

    `FormattedValue.expr` 部分 (f-string の `{expr}`) の中の文字列も
    Constant として拾われる。これは「リテラル日本語の検出」目的では
    正しい挙動 (例: `f"x{'日本語' if c else 'ok'}"` の `'日本語'` を捕捉)。
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            yield (getattr(sub, "lineno", 0), sub.value)


def _call_target_name(node: ast.Call) -> str:
    """Return the dotted name being called (best effort): `Foo.bar(...)` → `Foo.bar`,
    `bar(...)` → `bar`. Used to identify HTTPException / JSONResponse / Response."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        # Walk left to assemble the chain
        parts: list[str] = [func.attr]
        cur: ast.AST = func.value
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


# Positional signatures for response-shape APIs whose user-facing string is
# in a known argument index. Copilot PR #125 round 2 で `raise HTTPException(403, "...")`
# 形式 (positional) も拾うために必要。
POSITIONAL_TARGETS: dict[str, list[int]] = {
    # function_name (last component) -> indices of args to inspect
    "HTTPException": [1],     # HTTPException(status_code, detail, ...)
    "JSONResponse": [0],      # JSONResponse(content, status_code, ...)
    "Response": [0],          # Response(content, status_code, ...)
}


class GuardError(Exception):
    """Raised when the guard cannot scan a file (parse error / IO error etc).

    Treated as guard failure rather than silent skip so coverage cannot be
    bypassed by introducing unparseable code (Copilot PR #125 round 4 指摘)。
    """


def _parse_file(path: Path) -> tuple[str, ast.Module]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise GuardError(f"cannot read {path}: {e}") from e
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        raise GuardError(f"cannot parse {path}: {e}") from e
    return text, tree


def scan_kwargs(path: Path, kwarg_names: set[str]) -> list[tuple[int, str]]:
    """指定の kwarg 名の value、および POSITIONAL_TARGETS で定義された関数の
    特定位置にある positional 引数の文字列リテラルから日本語を検出。
    """
    text, tree = _parse_file(path)
    lines = text.splitlines()
    out: list[tuple[int, str]] = []

    def collect(value: ast.AST) -> None:
        for lineno, literal in iter_string_literals(value):
            if not JP_CHARS.search(literal):
                continue
            src = lines[lineno - 1] if 1 <= lineno <= len(lines) else literal
            out.append((lineno, src.strip()))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # keyword args
        for kw in node.keywords:
            if kw.arg in kwarg_names:
                collect(kw.value)
        # positional args (for known response-shape APIs)
        target = _call_target_name(node).rsplit(".", 1)[-1]
        for idx in POSITIONAL_TARGETS.get(target, []):
            if idx < len(node.args):
                collect(node.args[idx])
    return out


def scan_all_strings(path: Path) -> list[tuple[int, str]]:
    """ファイル中の全文字列リテラル (式 / call / 代入の右辺など) から日本語を検出。

    モジュール冒頭の docstring (Expr(Constant(str)) が最初に来る) は対象外。
    関数 docstring は対象 (公開関数の説明として MCP が露出させるため)。
    """
    text, tree = _parse_file(path)
    lines = text.splitlines()
    out: list[tuple[int, str]] = []

    # モジュールトップの docstring を skip 用に記憶
    module_docstring_node: ast.AST | None = None
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        module_docstring_node = tree.body[0].value

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if node is module_docstring_node:
            continue
        if not JP_CHARS.search(node.value):
            continue
        lineno = getattr(node, "lineno", 0)
        src = lines[lineno - 1] if 1 <= lineno <= len(lines) else node.value
        out.append((lineno, src.strip()))

    return out


def collect_files(*roots: Path, pattern: str = "*.py") -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.exists():
            out.extend(sorted(root.rglob(pattern)))
    return out


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]

    total: list[tuple[str, Path, int, str]] = []
    parse_failures: list[tuple[Path, str]] = []

    def run_kwargs(path: Path, kwarg_names: set[str], category: str) -> None:
        try:
            results = scan_kwargs(path, kwarg_names)
        except GuardError as e:
            parse_failures.append((path, str(e)))
            return
        for lineno, snip in results:
            total.append((category, path, lineno, snip))

    def run_all_strings(path: Path, category: str) -> None:
        try:
            results = scan_all_strings(path)
        except GuardError as e:
            parse_failures.append((path, str(e)))
            return
        for lineno, snip in results:
            total.append((category, path, lineno, snip))

    # 1. api/lib/routers の detail / content kwarg
    for path in collect_files(repo_root / "api" / "lib" / "routers"):
        run_kwargs(path, {"detail", "content"}, "api/lib/routers (detail/content)")

    # 2. api/lib/models の description kwarg (Pydantic Field)
    for path in collect_files(repo_root / "api" / "lib" / "models"):
        run_kwargs(path, {"description"}, "api/lib/models (description=)")

    # 3. MCP の公開コード表面 (server.py / tools/*.py / errors.py)。
    #    @mcp.tool() 本体は mcp/server.py、helper 実装は mcp/tools/、
    #    error response 整形は mcp/errors.py。Phase 2 (#106) の対象。
    mcp_targets: list[Path] = []
    for sub in ("server.py", "errors.py"):
        p = repo_root / "mcp" / sub
        if p.exists():
            mcp_targets.append(p)
    mcp_targets.extend(collect_files(repo_root / "mcp" / "tools"))
    for path in mcp_targets:
        rel_top = path.relative_to(repo_root / "mcp").parts[0]
        run_all_strings(path, f"mcp/{rel_top}")

    # Parse failures must NOT silently pass — Copilot PR #125 round 4 指摘。
    if parse_failures:
        print(
            f"::error title=i18n guard::Could not scan {len(parse_failures)} file(s); "
            "parse/IO failures are treated as guard failures to prevent silent bypass."
        )
        for path, reason in parse_failures:
            rel = path.relative_to(repo_root)
            print(f"  {rel}: {reason}")
        return 2

    if not total:
        print("i18n guard: OK (no Japanese strings detected in public API/MCP surfaces)")
        return 0

    by_cat: dict[str, list[tuple[Path, int, str]]] = {}
    for cat, path, lineno, snip in total:
        by_cat.setdefault(cat, []).append((path, lineno, snip))

    print(
        f"::error title=i18n guard::Found {len(total)} "
        "Japanese string violation(s) in public API/MCP surfaces."
    )
    for cat, items in by_cat.items():
        print(f"\n=== Violations: {cat} ===")
        for path, lineno, snip in items:
            rel = path.relative_to(repo_root)
            print(f"  {rel}:{lineno}: {snip}")
    print(
        "\nIf a literal must remain (e.g. a non-ASCII example in the MCP "
        "geocoder), move it into a Python comment (`# ...`) — the guard "
        "inspects AST string nodes only, never comments or module-level docstrings."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
