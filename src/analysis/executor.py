"""Executes LLM-generated pandas code with NO sandbox (trusted local machine).

Design choice per the roadmap: generated Python runs directly. Failures are
CAPTURED (returned as a traceback string) — never raised — so the graph's
inspect/retry loop can feed the error back to write_code.
"""
from __future__ import annotations

import contextlib
import io
import re
import traceback
from typing import Any

import pandas as pd

_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences, returning the raw Python source."""
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def execute_code(
    code: str, dataframes: dict[str, pd.DataFrame]
) -> tuple[Any, str, str | None]:
    """Run `code` in a namespace holding the named DataFrames.

    Returns (result, stdout, error) where `error` is None on success and a
    traceback string on failure. Failures are captured, never raised.
    """
    source = strip_code_fences(code)
    namespace: dict[str, Any] = {"pd": pd, "__builtins__": __builtins__}
    namespace.update(dataframes)

    stdout_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(source, namespace)  # noqa: S102 - intentional, no sandbox
    except Exception:  # noqa: BLE001 - capture, don't raise
        return None, stdout_buf.getvalue(), traceback.format_exc()

    if "result" not in namespace:
        return (
            None,
            stdout_buf.getvalue(),
            "NameError: generated code did not assign to `result`.",
        )
    return namespace["result"], stdout_buf.getvalue(), None


def render_result(result: Any, limit: int = 4000) -> str:
    """Render a result value to a compact string for storage / narration."""
    if result is None:
        return ""
    try:
        if isinstance(result, (pd.DataFrame, pd.Series)):
            text = result.to_string()
        else:
            text = str(result)
    except Exception:  # noqa: BLE001
        text = repr(result)
    if len(text) > limit:
        text = text[:limit] + "\n... [truncated]"
    return text
