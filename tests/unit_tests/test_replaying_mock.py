from typing import Any, Tuple

import pytest

from mock_isolator.replaying_mock import ReplayingMock


@pytest.fixture
def recorded_attribute_accesses() -> dict[str, list[Any] | dict[str, Any] | Any]:
    return {
        "attr1": [1, 2, 3],
        "attr2": {"__repeat__": "repeated_value"},
        "attr3": "single_value",
    }


@pytest.fixture
def recorded_calls() -> list[Tuple[Tuple[Any, ...], dict[str, Any]]]:
    return [
        ((), {"result": "call_result_1"}),
        ((), {"result": "call_result_2"}),
    ]


@pytest.fixture
def replaying_mock(
    recorded_attribute_accesses: dict[str, list[Any] | dict[str, Any] | Any],
    recorded_calls: list[Tuple[Tuple[Any, ...], dict[str, Any]]],
) -> ReplayingMock:
    return ReplayingMock(recorded_attribute_accesses, recorded_calls)


def test_getattr_list(replaying_mock: ReplayingMock) -> None:
    assert replaying_mock.attr1 == 1
    assert replaying_mock.attr1 == 2
    assert replaying_mock.attr1 == 3


def test_getattr_repeat(replaying_mock: ReplayingMock) -> None:
    assert replaying_mock.attr2 == "repeated_value"
    assert replaying_mock.attr2 == "repeated_value"


def test_getattr_single(replaying_mock: ReplayingMock) -> None:
    assert replaying_mock.attr3 == "single_value"


def test_getattr_not_found(replaying_mock: ReplayingMock) -> None:
    with pytest.raises(AttributeError):
        _ = replaying_mock.attr_not_found


def test_call(replaying_mock: ReplayingMock) -> None:
    assert replaying_mock() == {"result": "call_result_1"}
    assert replaying_mock() == {"result": "call_result_2"}


def test_call_no_more_recorded(replaying_mock: ReplayingMock) -> None:
    _ = replaying_mock()  # First call
    _ = replaying_mock()  # Second call
    with pytest.raises(ValueError):
        _ = replaying_mock()  # No more calls
