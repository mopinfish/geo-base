#!/usr/bin/env python3
"""i18n guard (Phase 2 / Issue #106).

API レスポンス相当箇所と MCP tool 記述に日本語混入がないことを fail-fast で
検証する。Phase 1 完了時点で API/Pydantic は全て英語化済みなので、本ガードは
「リグレッション防止」が主目的。

検出範囲:
  1. api/lib/routers/**/*.py の `detail=...` を含む行の文字列リテラル
  2. api/lib/models/**/*.py の Pydantic Field(..., description="...") の文字列
  3. api/lib/routers/**/*.py の JSONResponse / Response(content=...) の文字列
  4. mcp/tools/**/*.py の @mcp.tool() を含むファイル全体の文字列リテラル

検出パターン: Hiragana / Katakana / CJK 統合漢字 (基本多言語面) が
文字列リテラル中に含まれる場合。`tokenize` モジュールで Python を字句解析し、
コメント (`# ...`) は除外。spec 14 章「コードコメントの一括英語化はしない」
に従い、純コメントは検査しない。

Usage:
  python3 .github/workflows/scripts/i18n_guard.py
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path
from typing import Callable

# Hiragana (U+3040–U+309F), Katakana (U+30A0–U+30FF + prolonged sound mark),
# CJK 統合漢字 (U+4E00–U+9FFF)。
JP_CHARS = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")


def iter_string_tokens(path: Path):
    """Yield `(lineno, token_string, raw_source)` for each STRING token in `path`.

    `tokenize` correctly handles Python lexical rules: triple-quoted strings,
    nested apostrophes inside double-quoted strings, escape sequences, etc.
    """
    try:
        with path.open("rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.STRING:
                    yield (tok.start[0], tok.string)
    except (SyntaxError, tokenize.TokenizeError, UnicodeDecodeError, OSError):
        # Best-effort: skip files we can't tokenize.
        return


def scan_file(
    path: Path,
    *,
    line_filter: Callable[[str], bool] | None = None,
) -> list[tuple[int, str]]:
    """Return list of `(lineno, line_snippet)` where a string literal contains
    Japanese. If `line_filter` is given, only include violations whose source
    line passes the filter (e.g. line contains "detail=").
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    out: list[tuple[int, str]] = []
    for lineno, literal in iter_string_tokens(path):
        if not JP_CHARS.search(literal):
            continue
        if not (1 <= lineno <= len(lines)):
            continue
        source_line = lines[lineno - 1]
        if line_filter is not None and not line_filter(source_line):
            continue
        out.append((lineno, source_line.strip()))
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

    # 1. api/lib/routers の detail=...
    for path in collect_files(repo_root / "api" / "lib" / "routers"):
        for lineno, snip in scan_file(path, line_filter=lambda L: "detail=" in L):
            total.append(("api/lib/routers (detail=)", path, lineno, snip))

    # 2. Pydantic Field(..., description=...)
    for path in collect_files(repo_root / "api" / "lib" / "models"):
        for lineno, snip in scan_file(path, line_filter=lambda L: "description=" in L):
            total.append(("api/lib/models (description=)", path, lineno, snip))

    # 3. JSONResponse / Response の content
    response_re = re.compile(r"\bJSONResponse\b|\bResponse\(")
    for path in collect_files(repo_root / "api" / "lib" / "routers"):
        for lineno, snip in scan_file(
            path, line_filter=lambda L: bool(response_re.search(L))
        ):
            total.append(("api/lib/routers (JSONResponse/Response)", path, lineno, snip))

    # 4. MCP の公開コード表面 (server.py / tools/*.py / errors.py)。
    #    @mcp.tool() 本体は mcp/server.py、helper 実装は mcp/tools/、
    #    error response 整形は mcp/errors.py。Phase 2 (#106) の対象。
    mcp_targets: list[Path] = []
    for sub in ("server.py", "errors.py"):
        p = repo_root / "mcp" / sub
        if p.exists():
            mcp_targets.append(p)
    mcp_targets.extend(collect_files(repo_root / "mcp" / "tools"))
    for path in mcp_targets:
        for lineno, snip in scan_file(path):
            rel_dir = "mcp/" + path.relative_to(repo_root / "mcp").parts[0]
            total.append((rel_dir, path, lineno, snip))

    if not total:
        print("i18n guard: OK (no Japanese strings detected in public API/MCP surfaces)")
        return 0

    # Group by category
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
        "only flags STRING tokens, never comments."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
