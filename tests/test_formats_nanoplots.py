import pytest

from typing import Any
from great_tables._formats import _generate_data_vals


@pytest.mark.parametrize(
    "src", ["1 2 3", "1  2, 3", "a1 b2 c3", [1, 2, 3], {"x": [1, 2, 3]}, {"any_name": [1, 2, 3]}]
)
def test_generate_data_vals(src: Any):
    assert _generate_data_vals(src) == [1, 2, 3]


@pytest.mark.xfail
def test_generate_data_vals_fails_ambig():
    with pytest.raises(ValueError):
        _generate_data_vals("a1b2c3")


def test_generate_data_vals_fails_novals():
    with pytest.raises(ValueError):
        _generate_data_vals("abc")


def test_generate_data_vals_fails_date_strings():
    with pytest.raises(ValueError) as exc_info:
        _generate_data_vals(["2022-01-01"])

    assert "Only the x-axis of a nanoplot allows strings." in exc_info.value.args[0]


def test_generate_data_vals_fails_scalar_date_string():
    with pytest.raises(ValueError) as exc_info:
        _generate_data_vals("2022-01-01")

    assert exc_info.value.args[0] == "could not convert string to float: '2022-01-01'"


@pytest.mark.parametrize("nested_el", [[2, 3], (2, 3), "2 3", "abc"])
def test_generate_data_vals_fails_nested_list(nested_el):
    with pytest.raises(ValueError) as exc_info:
        _generate_data_vals([1, nested_el])

    assert f"Value received: {nested_el}" in exc_info.value.args[0]


@pytest.mark.xfail
def test_nanoplot_ref_line_area():
    # TODO: add this test
    assert False
