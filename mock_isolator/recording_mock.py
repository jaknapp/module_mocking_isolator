from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from types import TracebackType
from typing import Any, Tuple, Type
import asyncio

from bson import ObjectId


class RecordingMocker(ABC):
    @abstractmethod
    def wrap_item_with_recording_mocks(self, item: Any) -> Any:
        pass


class RecordingMock:
    """
    Wrap an item (ie. class, function, module, etc.) in a mock that will record the
    values it returns. The returned values are also wrapped in a RecordingMock by using
    the mocker.
    """

    def __init__(self, wrapped_item: Any, mocker: RecordingMocker):
        self._wrapped_item = wrapped_item
        self._mocker = mocker
        self.recorded_attribute_accesses: dict[str, list[Any]] = {}
        self.recorded_async_attribute_access_indexes: dict[str, set[int]] = {}
        self.recorded_calls: list[Tuple[Tuple[Any, ...], dict[str, Any]]] = []

    def __getattribute__(self, name: str) -> Any:
        if name in [
            "_wrapped_item",
            "recorded_attribute_accesses",
            "recorded_async_attribute_access_indexes",
            "recorded_calls",
            "_mocker",
            "__class__",
            "__dict__",
            "__getattribute__",
        ]:
            return object.__getattribute__(self, name)
        wrapped_item = object.__getattribute__(self, "_wrapped_item")
        attribute = getattr(wrapped_item, name)
        
        # Handle coroutines
        if callable(attribute) and asyncio.iscoroutinefunction(attribute):
            async def wrapped_coroutine(*args, **kwargs):
                result = await attribute(*args, **kwargs)
                wrapped_result = self._mocker.wrap_item_with_recording_mocks(item=result)
                if name not in self.recorded_attribute_accesses:
                    self.recorded_attribute_accesses[name] = []
                    self.recorded_async_attribute_access_indexes[name] = set()
                self.recorded_async_attribute_access_indexes[name].add(len(self.recorded_attribute_accesses[name]))
                self.recorded_attribute_accesses[name].append(wrapped_result)
                return wrapped_result
            return wrapped_coroutine
            
        wrapped_attribute = self._mocker.wrap_item_with_recording_mocks(item=attribute)
        if name not in self.recorded_attribute_accesses:
            self.recorded_attribute_accesses[name] = []
        self.recorded_attribute_accesses[name].append(wrapped_attribute)
        return wrapped_attribute

    def __setattr__(self, name: str, value: Any) -> None:
        if name in [
            "_wrapped_item",
            "_mocker",
            "recorded_attribute_accesses",
            "recorded_async_attribute_access_indexes",
            "recorded_calls",
        ]:
            object.__setattr__(self, name, value)
        else:
            setattr(self._wrapped_item, name, value)

    def __call__(self, *args: Any, **kwargs: dict[str, Any]) -> Any:
        result = self._wrapped_item(*args, **kwargs)
        wrapped_result = self._mocker.wrap_item_with_recording_mocks(item=result)
        self.recorded_calls.append(((args, kwargs), wrapped_result))
        return wrapped_result

    def __get__(self, instance: Any | None, owner: Type[Any] | None = None) -> Any:
        return self._wrapped_item
    
    async def __aenter__(self) -> Any:
        result = await self._wrapped_item.__aenter__()
        wrapped_result = self._mocker.wrap_item_with_recording_mocks(result)
        self.recorded_attribute_accesses.setdefault("__aenter__", []).append(wrapped_result)
        return wrapped_result

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        result = await self._wrapped_item.__aexit__(exc_type, exc_val, exc_tb)
        self.recorded_attribute_accesses.setdefault("__aexit__", []).append(result)
        return result

    def __enter__(self) -> Any:
        result = self._wrapped_item.__enter__()
        wrapped_result = self._mocker.wrap_item_with_recording_mocks(result)
        self.recorded_attribute_accesses.setdefault("__enter__", []).append(wrapped_result)
        return wrapped_result

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        result = self._wrapped_item.__exit__(exc_type, exc_val, exc_tb)
        self.recorded_attribute_accesses.setdefault("__exit__", []).append(result)
        return result

    def __aiter__(self) -> Any:
        aiter_value = aiter(self._wrapped_item)
        wrapped_aiter = self._mocker.wrap_item_with_recording_mocks(item=aiter_value)
        if "__aiter__" not in self.recorded_attribute_accesses:
            self.recorded_attribute_accesses["__aiter__"] = []
            self.recorded_async_attribute_access_indexes["__aiter__"] = set()
        self.recorded_async_attribute_access_indexes["__aiter__"].add(len(self.recorded_attribute_accesses["__aiter__"]))
        self.recorded_attribute_accesses["__aiter__"].append(wrapped_aiter)
        return wrapped_aiter

    async def __anext__(self) -> Any:
        try:
            result = await anext(self._wrapped_item)
            wrapped_result = self._mocker.wrap_item_with_recording_mocks(item=result)
            if "__anext__" not in self.recorded_attribute_accesses:
                self.recorded_attribute_accesses["__anext__"] = []
                self.recorded_async_attribute_access_indexes["__anext__"] = set()
            self.recorded_async_attribute_access_indexes["__anext__"].add(len(self.recorded_attribute_accesses["__anext__"]))
            self.recorded_attribute_accesses["__anext__"].append(wrapped_result)
            return wrapped_result
        except StopAsyncIteration:
            if "__anext__" not in self.recorded_attribute_accesses:
                self.recorded_attribute_accesses["__anext__"] = []
                self.recorded_async_attribute_access_indexes["__anext__"] = set()
            self.recorded_async_attribute_access_indexes["__anext__"].add(len(self.recorded_attribute_accesses["__anext__"]))
            self.recorded_attribute_accesses["__anext__"].append(StopAsyncIteration())
            raise


class BasicRecordingMocker(RecordingMocker):
    def __init__(
        self,
        concrete_types: list[Type] | None = None,
        additional_concrete_types: list[Type] | None = None,
    ):
        _concrete_types = (
            [int, str, float, bool, type(None), Decimal, date, datetime, ObjectId]
            if concrete_types is None
            else [*concrete_types]
        )
        _concrete_types.extend(additional_concrete_types or [])
        self._concrete_types = tuple(_concrete_types)

    def wrap_item_with_recording_mocks(self, item: Any) -> Any:
        if isinstance(item, self._concrete_types):
            return item
        elif isinstance(item, dict):
            return {
                key: self.wrap_item_with_recording_mocks(item)
                for key, item in item.items()
            }
        elif isinstance(item, list):
            return [self.wrap_item_with_recording_mocks(item) for item in item]
        elif isinstance(item, set):
            return {self.wrap_item_with_recording_mocks(item) for item in item}
        elif isinstance(item, frozenset):
            return frozenset(
                {self.wrap_item_with_recording_mocks(item) for item in item}
            )
        else:
            return RecordingMock(wrapped_item=item, mocker=self)
