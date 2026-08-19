"""Executor unit tests — no LLM. Runs real pandas, captures errors."""
import pandas as pd

from analysis.executor import execute_code, render_result, strip_code_fences


def test_execute_simple_pandas():
    df = pd.DataFrame({"a": [1, 2, 3, 4]})
    result, stdout, err = execute_code("result = df['a'].sum()", {"df": df})
    assert err is None
    assert result == 10


def test_execute_captures_error_not_raised():
    df = pd.DataFrame({"a": [1, 2, 3]})
    # references a column that does not exist -> KeyError captured as traceback
    result, stdout, err = execute_code("result = df['missing'].sum()", {"df": df})
    assert result is None
    assert err is not None
    assert "KeyError" in err or "missing" in err


def test_execute_missing_result_assignment():
    df = pd.DataFrame({"a": [1]})
    result, stdout, err = execute_code("x = df['a'].sum()", {"df": df})
    assert result is None
    assert err is not None and "result" in err


def test_strip_code_fences():
    fenced = "```python\nresult = 1 + 1\n```"
    assert strip_code_fences(fenced) == "result = 1 + 1"
    assert strip_code_fences("result = 2") == "result = 2"


def test_render_result_scalar_and_frame():
    assert render_result(42) == "42"
    df = pd.DataFrame({"a": [1, 2]})
    assert "a" in render_result(df)
