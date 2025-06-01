import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from bson import ObjectId

from mock_isolator.recording_mock import BasicRecordingMocker, RecordingMock


@pytest.fixture
def mocker() -> BasicRecordingMocker:
    return BasicRecordingMocker()


def test_recording_mock_initialization(mocker: BasicRecordingMocker) -> None:
    item = "test"
    recording_mock = RecordingMock(wrapped_item=item, mocker=mocker)

    assert recording_mock._wrapped_item == item
    assert recording_mock._mocker == mocker
    assert recording_mock.recorded_attribute_accesses == {}
    assert recording_mock.recorded_calls == []


def test_recording_mock_getattr(mocker: BasicRecordingMocker) -> None:
    class TestClass:
        def __init__(self):
            self.attr = "value"

    test_instance = TestClass()
    recording_mock = RecordingMock(wrapped_item=test_instance, mocker=mocker)

    assert recording_mock.attr == "value"
    assert "attr" in recording_mock.recorded_attribute_accesses
    assert recording_mock.recorded_attribute_accesses["attr"] == ["value"]


def test_recording_mock_call(mocker: BasicRecordingMocker) -> None:
    def test_function(a: int, b: int) -> int:
        return a + b

    recording_mock = RecordingMock(wrapped_item=test_function, mocker=mocker)
    result = recording_mock(1, 2)

    assert result == 3
    assert len(recording_mock.recorded_calls) == 1
    assert recording_mock.recorded_calls[0] == (((1, 2), {}), 3)


def test_recording_mock_get(mocker: BasicRecordingMocker) -> None:
    class TestClass:
        pass

    test_instance = TestClass()
    recording_mock = RecordingMock(wrapped_item=test_instance, mocker=mocker)

    class TestClass2:
        t = recording_mock

    test_instance_2 = TestClass2()

    assert test_instance_2.t is test_instance


def test_basic_recording_mocker_wrap_item_with_recording_mocks(
    mocker: BasicRecordingMocker,
) -> None:
    assert mocker.wrap_item_with_recording_mocks(123) == 123
    assert mocker.wrap_item_with_recording_mocks("string") == "string"
    assert mocker.wrap_item_with_recording_mocks(12.34) == 12.34
    assert mocker.wrap_item_with_recording_mocks(True) is True
    assert mocker.wrap_item_with_recording_mocks(None) is None
    assert mocker.wrap_item_with_recording_mocks(Decimal("10.5")) == Decimal("10.5")
    assert mocker.wrap_item_with_recording_mocks(date.today()) == date.today()

    now = datetime.now()
    wrapped_now = mocker.wrap_item_with_recording_mocks(now)
    assert isinstance(wrapped_now, datetime)
    assert (wrapped_now - now) < timedelta(seconds=1)

    dict_item = {"key": "value"}
    wrapped_dict = mocker.wrap_item_with_recording_mocks(dict_item)
    assert wrapped_dict == dict_item
    assert isinstance(wrapped_dict, dict)

    list_item = [1, 2, 3]
    wrapped_list = mocker.wrap_item_with_recording_mocks(list_item)
    assert wrapped_list == list_item
    assert isinstance(wrapped_list, list)

    set_item = {1, 2, 3}
    wrapped_set = mocker.wrap_item_with_recording_mocks(set_item)
    assert wrapped_set == set_item
    assert isinstance(wrapped_set, set)

    frozenset_item = frozenset([1, 2, 3])
    wrapped_frozenset = mocker.wrap_item_with_recording_mocks(frozenset_item)
    assert wrapped_frozenset == frozenset_item
    assert isinstance(wrapped_frozenset, frozenset)

    object_id = ObjectId()
    wrapped_object_id = mocker.wrap_item_with_recording_mocks(object_id)
    assert wrapped_object_id == object_id
    assert isinstance(wrapped_object_id, ObjectId)

def test_recording_mock_context_manager_sync(mocker: BasicRecordingMocker) -> None:
    class SyncContext:
        def __enter__(self):
            return "entered"

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    mock = RecordingMock(SyncContext(), mocker)

    with mock as result:
        assert result == "entered"

    assert "__enter__" in mock.recorded_attribute_accesses
    assert mock.recorded_attribute_accesses["__enter__"][0] == "entered"

    assert "__exit__" in mock.recorded_attribute_accesses
    assert mock.recorded_attribute_accesses["__exit__"][0] is False

@pytest.mark.asyncio
async def test_recording_mock_context_manager_async(mocker: BasicRecordingMocker) -> None:
    class AsyncContext:
        async def __aenter__(self):
            return "async entered"

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return True

    mock = RecordingMock(AsyncContext(), mocker)

    async with mock as result:
        assert result == "async entered"

    assert "__aenter__" in mock.recorded_attribute_accesses
    assert mock.recorded_attribute_accesses["__aenter__"][0] == "async entered"

    assert "__aexit__" in mock.recorded_attribute_accesses
    assert mock.recorded_attribute_accesses["__aexit__"][0] is True

def test_recording_mock_context_manager_sync_with_exception(mocker: BasicRecordingMocker) -> None:
    class FailingContext:
        def __enter__(self):
            return "ok"

        def __exit__(self, exc_type, exc_val, exc_tb):
            assert exc_type is ValueError
            return True  # suppress the exception

    mock = RecordingMock(FailingContext(), mocker)

    try:
        with mock:
            raise ValueError("fail!")
    except ValueError:
        pytest.fail("Exception should have been suppressed")

    assert "__exit__" in mock.recorded_attribute_accesses
    assert mock.recorded_attribute_accesses["__exit__"][0] is True

def test_recording_mock_context_manager_async_with_exception(mocker: BasicRecordingMocker) -> None:
    class AsyncFailingContext:
        async def __aenter__(self):
            return "async ok"

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            assert exc_type is KeyError
            return True  # suppress the exception

    async def run_test():
        mock = RecordingMock(AsyncFailingContext(), mocker)

        try:
            async with mock:
                raise KeyError("fail async")
        except KeyError:
            pytest.fail("Exception should have been suppressed")

        assert "__aexit__" in mock.recorded_attribute_accesses
        assert mock.recorded_attribute_accesses["__aexit__"][0] is True

    asyncio.run(run_test())

@pytest.mark.asyncio
async def test_recording_mock_async_method(mocker: BasicRecordingMocker) -> None:
    class AsyncClass:
        async def async_method(self, x: int) -> int:
            return x + 1

    instance = AsyncClass()
    mock = RecordingMock(instance, mocker)

    result = await mock.async_method(5)
    assert result == 6
    assert "async_method" in mock.recorded_attribute_accesses
    assert mock.recorded_attribute_accesses["async_method"] == [6]

@pytest.mark.asyncio
async def test_recording_mock_async_method_chain(mocker: BasicRecordingMocker) -> None:
    class AsyncClass:
        async def method1(self) -> int:
            return 1
        async def method2(self, x: int) -> int:
            return x + 1

    instance = AsyncClass()
    mock = RecordingMock(instance, mocker)

    result1 = await mock.method1()
    result2 = await mock.method2(result1)
    assert result1 == 1
    assert result2 == 2
    assert mock.recorded_attribute_accesses["method1"] == [1]
    assert mock.recorded_attribute_accesses["method2"] == [2]

@pytest.mark.asyncio
async def test_recording_mock_async_method_with_exception(mocker: BasicRecordingMocker) -> None:
    class AsyncClass:
        async def failing_method(self) -> None:
            raise ValueError("test error")

    instance = AsyncClass()
    mock = RecordingMock(instance, mocker)

    with pytest.raises(ValueError, match="test error"):
        await mock.failing_method()