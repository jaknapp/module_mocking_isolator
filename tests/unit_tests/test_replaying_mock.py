import asyncio
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

def test_enter_and_exit_with_list_values() -> None:
    mock = ReplayingMock(
        recorded_attribute_accesses={
            "__enter__": ["sync enter result"],
            "__exit__": [True],
        },
        recorded_calls=[],
    )

    with mock as result:
        assert result == "sync enter result"

    assert mock._recorded_attribute_accesses["__exit__"] == []

def test_enter_and_exit_with_single_values() -> None:
    mock = ReplayingMock(
        recorded_attribute_accesses={
            "__enter__": "sync single enter",
            "__exit__": False,
        },
        recorded_calls=[],
    )

    with mock as result:
        assert result == "sync single enter"

    assert mock.__exit__(None, None, None) is False

def test_enter_missing_key_raises() -> None:
    mock = ReplayingMock(recorded_attribute_accesses={}, recorded_calls=[])

    with pytest.raises(AttributeError, match="No recorded __enter__ result found."):
        with mock:
            pass

def test_exit_missing_key_returns_false() -> None:
    mock = ReplayingMock(recorded_attribute_accesses={}, recorded_calls=[])

    assert mock.__exit__(None, None, None) is False

def test_aenter_and_aexit_with_list_values() -> None:
    mock = ReplayingMock(
        recorded_attribute_accesses={
            "__aenter__": ["async enter result"],
            "__aexit__": [True],
        },
        recorded_calls=[],
    )

    async def run():
        async with mock as result:
            assert result == "async enter result"
        # __aexit__ should return the first (and only) value
        # Implicitly tested by successful exit

    asyncio.run(run())

def test_aenter_and_aexit_with_single_values() -> None:
    mock = ReplayingMock(
        recorded_attribute_accesses={
            "__aenter__": "async single enter",
            "__aexit__": False,
        },
        recorded_calls=[],
    )

    async def run():
        async with mock as result:
            assert result == "async single enter"

    asyncio.run(run())

def test_aenter_missing_key_raises() -> None:
    mock = ReplayingMock(recorded_attribute_accesses={}, recorded_calls=[])

    async def run():
        with pytest.raises(AttributeError, match="No recorded __aenter__ result found."):
            async with mock:
                pass

    asyncio.run(run())

def test_aexit_missing_key_returns_false() -> None:
    mock = ReplayingMock(recorded_attribute_accesses={}, recorded_calls=[])

    async def run():
        result = await mock.__aexit__(None, None, None)
        assert result is False

    asyncio.run(run())

@pytest.mark.asyncio
async def test_replaying_mock_async_method() -> None:
    class AsyncClass:
        async def async_method(self, x: int) -> int:
            return x + 1

    mock = ReplayingMock(
        recorded_attribute_accesses={
            "async_method": [6]
        },
        recorded_calls=[],
        target_type=AsyncClass
    )

    result = await mock.async_method(5)
    assert result == 6

@pytest.mark.asyncio
async def test_replaying_mock_async_method_chain() -> None:
    class AsyncClass:
        async def method1(self) -> int:
            return 1
        async def method2(self, x: int) -> int:
            return x + 1

    mock = ReplayingMock(
        recorded_attribute_accesses={
            "method1": [1],
            "method2": [2]
        },
        recorded_calls=[],
        target_type=AsyncClass
    )

    result1 = await mock.method1()
    result2 = await mock.method2(result1)
    assert result1 == 1
    assert result2 == 2

@pytest.mark.asyncio
async def test_replaying_mock_async_method_with_exception() -> None:
    class AsyncClass:
        async def failing_method(self) -> None:
            raise ValueError("test error")

    mock = ReplayingMock(
        recorded_attribute_accesses={
            "failing_method": [ValueError("test error")]
        },
        recorded_calls=[],
        target_type=AsyncClass
    )

    with pytest.raises(ValueError, match="test error"):
        await mock.failing_method()

@pytest.mark.asyncio
async def test_replaying_mock_async_method_without_target_type() -> None:
    mock = ReplayingMock(
        recorded_attribute_accesses={
            "async_method": [6]
        },
        recorded_calls=[]
    )

    # Without target_type, we can't know if it should be async
    with pytest.raises(TypeError, match="'int' object is not callable"):
        await mock.async_method(5)
