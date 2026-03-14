"""Hygiene ratchet: budgets for production code in src/. Lower budgets over time; never raise."""

from __future__ import annotations

import re
from pathlib import Path

MAX_PRINT = 0
MAX_TYPE_IGNORE = 0
MAX_NOQA = 0
MAX_EXCEPT_EXCEPTION = 10


def _source_files() -> list[Path]:
    return [
        p for p in (Path(__file__).parent.parent / "src").rglob("*.py") if p.is_file()
    ]


ROOT = Path(__file__).parent.parent


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _count(files: list[Path], pattern: str) -> list[tuple[Path, int]]:
    hits: list[tuple[Path, int]] = []
    for p in files:
        for i, line in enumerate(_lines(p), 1):
            if pattern in line:
                hits.append((p, i))
    return hits


def _count_regex(files: list[Path], rx: re.Pattern[str]) -> list[tuple[Path, int]]:
    hits: list[tuple[Path, int]] = []
    for p in files:
        for i, line in enumerate(_lines(p), 1):
            if rx.search(line):
                hits.append((p, i))
    return hits


SOURCE_FILES = _source_files()


def test_print_budget() -> None:
    hits = _count_regex(SOURCE_FILES, re.compile(r"\bprint\("))
    count = len(hits)
    assert count <= MAX_PRINT, (
        f"print() budget exceeded ({count}/{MAX_PRINT}): "
        + ", ".join(f"{p.relative_to(ROOT)}:{i}" for p, i in hits)
    )


def test_type_ignore_budget() -> None:
    hits = _count(SOURCE_FILES, "# type: ignore")
    count = len(hits)
    assert count <= MAX_TYPE_IGNORE, (
        f"# type: ignore budget exceeded ({count}/{MAX_TYPE_IGNORE}): "
        + ", ".join(f"{p.relative_to(ROOT)}:{i}" for p, i in hits)
    )


def test_noqa_budget() -> None:
    hits = _count(SOURCE_FILES, "# noqa")
    count = len(hits)
    assert count <= MAX_NOQA, (
        f"# noqa budget exceeded ({count}/{MAX_NOQA}): "
        + ", ".join(f"{p.relative_to(ROOT)}:{i}" for p, i in hits)
    )


def test_except_exception_budget() -> None:
    hits = _count(SOURCE_FILES, "except Exception:")
    count = len(hits)
    assert count <= MAX_EXCEPT_EXCEPTION, (
        f"except Exception: budget exceeded ({count}/{MAX_EXCEPT_EXCEPTION}): "
        + ", ".join(f"{p.relative_to(ROOT)}:{i}" for p, i in hits)
    )
