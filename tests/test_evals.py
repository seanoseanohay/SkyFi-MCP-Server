"""
Tests for SkyFi MCP eval cases.

Validates that:
- Every eval case has required fields and valid category.
- Every expected_tool (and forbidden_tool) is a registered MCP tool on the server.
- Eval dataset has sufficient coverage (count and categories).

These tests keep evals in sync with the server API and ensure tool names in evals
match what the server exposes so that tool-description improvements are measurable.
"""

import pytest

from src.server import mcp
from tests.eval_cases import EVAL_CASES, EVAL_CATEGORIES


def _registered_tool_names() -> set[str]:
    """Return the set of tool names registered on the MCP server."""
    return set(mcp._tool_manager._tools.keys())


def test_eval_cases_have_required_fields() -> None:
    """Every eval case must have id, prompt, category, and expected_tools."""
    required = {"id", "prompt", "category", "expected_tools"}
    for case in EVAL_CASES:
        missing = required - set(case.keys())
        assert not missing, f"eval {case.get('id', '?')} missing fields: {missing}"


def test_eval_cases_category_valid() -> None:
    """Every eval case category must be one of golden, adversarial, multi_tool, multi_step."""
    for case in EVAL_CASES:
        assert case["category"] in EVAL_CATEGORIES, (
            f"eval {case['id']}: category '{case['category']}' not in {EVAL_CATEGORIES}"
        )


def test_eval_cases_expected_tools_are_lists() -> None:
    """expected_tools must be a list of strings."""
    for case in EVAL_CASES:
        tools = case["expected_tools"]
        assert isinstance(tools, list), f"eval {case['id']}: expected_tools must be a list"
        for t in tools:
            assert isinstance(t, str), f"eval {case['id']}: each expected_tool must be a string"


def test_eval_cases_all_expected_tools_registered() -> None:
    """Every tool name in expected_tools across all evals must be registered on the server."""
    registered = _registered_tool_names()
    for case in EVAL_CASES:
        for tool in case["expected_tools"]:
            assert tool in registered, (
                f"eval {case['id']}: expected_tool '{tool}' is not registered on the server. "
                f"Registered: {sorted(registered)}"
            )


def test_eval_cases_all_forbidden_tools_registered() -> None:
    """If an eval has forbidden_tools, each must be a valid registered tool name."""
    registered = _registered_tool_names()
    for case in EVAL_CASES:
        forbidden = case.get("forbidden_tools")
        if not forbidden:
            continue
        for tool in forbidden:
            assert tool in registered, (
                f"eval {case['id']}: forbidden_tool '{tool}' is not registered on the server. "
                f"Registered: {sorted(registered)}"
            )


def test_eval_cases_minimum_count() -> None:
    """We have at least 40 eval cases for coverage."""
    assert len(EVAL_CASES) >= 40, (
        f"Expected at least 40 eval cases for tool-discoverability evals; got {len(EVAL_CASES)}"
    )


def test_eval_cases_each_category_present() -> None:
    """Each category (golden, adversarial, multi_tool, multi_step) has at least one eval."""
    by_category: dict[str, list[str]] = {}
    for c in EVAL_CASES:
        cat = c["category"]
        by_category.setdefault(cat, []).append(c["id"])
    for cat in EVAL_CATEGORIES:
        assert by_category.get(cat), f"No eval cases for category '{cat}'"


def test_eval_case_ids_unique() -> None:
    """Eval case ids must be unique."""
    ids = [c["id"] for c in EVAL_CASES]
    assert len(ids) == len(set(ids)), f"Duplicate eval ids: {[i for i in ids if ids.count(i) > 1]}"


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_each_eval_expected_tools_registered_parametrized(case: dict) -> None:
    """Per-eval parametrized test: all expected_tools for this case are registered."""
    registered = _registered_tool_names()
    for tool in case["expected_tools"]:
        assert tool in registered, f"expected_tool '{tool}' not registered"


@pytest.mark.skipif(
    not __import__("os").environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set; install openai and set key to run LLM evals",
)
def test_llm_eval_runner_one_case() -> None:
    """
    Run the LLM eval runner on one case (golden-01) to verify the pipeline.
    Requires: pip install openai, OPENAI_API_KEY set.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "scripts.llm_eval_runner", "--id", "golden-01"],
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent),
        timeout=60,
    )
    if result.returncode != 0 and "OPENAI_API_KEY" not in result.stderr:
        print(result.stdout, result.stderr)
    assert result.returncode == 0, (
        f"LLM eval runner failed: {result.stderr or result.stdout}"
    )
