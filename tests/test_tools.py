import pytest

from app.tools import calculate, current_time


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", "14"),
        ("(2 + 3) * 4", "20"),
        ("-3 + 8 / 2", "1"),
        ("2 ** 8", "256"),
        ("0.1 + 0.2", "0.3"),
    ],
)
def test_calculator_evaluates_arithmetic(expression, expected):
    assert float(calculate(expression)) == pytest.approx(float(expected))


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('id')",
        "(1).__class__",
        "[1, 2][0]",
        "True + 1",
        "2 ** 1000000",
        "9 ** 9 ** 9",
        "1 / 0",
        "1e309 + 1",
        "1 + " * 10000 + "1",
        "(",
        "",
    ],
)
def test_calculator_rejects_unsafe_or_unbounded_expressions(expression):
    with pytest.raises(ValueError):
        calculate(expression)


def test_time_tool_returns_requested_timezone():
    result = current_time("Asia/Kolkata")
    assert "202" in result
    assert "+05:30" in result or "Asia/Kolkata" in result


def test_time_tool_rejects_unknown_timezone():
    with pytest.raises(ValueError):
        current_time("Not/A_Timezone")
