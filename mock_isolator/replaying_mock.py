from types import TracebackType
from typing import Any, Tuple, Type
import asyncio


class ReplayingMock:
    """
    Replays a recording (ie. from a RecordingMock) such that the originally wrapped
    item is no longer needed.
    """

    def __init__(
        self,
        recorded_attribute_accesses: dict[str, list[Any] | dict[str, Any] | Any],
        recorded_calls: list[Tuple[Tuple[Any, ...], dict[str, Any]]],
        target_type: Type[Any] | None = None,
    ):
        self._recorded_attribute_accesses = recorded_attribute_accesses
        self._recorded_calls = recorded_calls
        self._current_call_index = 0
        self._target_type = target_type

    def __getattribute__(self, name: str) -> Any:
        if name in [
            "_recorded_attribute_accesses",
            "_recorded_calls",
            "_current_call_index",
            "_target_type",
            "__class__",
            "__dict__",
            "__getattribute__",
            "__call__",
            "__aenter__",
            "__aexit__",
            "__enter__",
            "__exit__",
        ]:
            return object.__getattribute__(self, name)
        if name in self._recorded_attribute_accesses:
            attribute = self._recorded_attribute_accesses[name]
            if isinstance(attribute, dict) and "__repeat__" in attribute:
                return attribute["__repeat__"]
            if isinstance(attribute, list):
                result = attribute.pop(0)
                # Check if this is an async value
                if isinstance(result, dict) and result.get("__type__") == "async_value":
                    async def wrapped_coroutine(*args, **kwargs):
                        if isinstance(result["value"], Exception):
                            raise result["value"]
                        return result["value"]
                    return wrapped_coroutine
                return result
            return attribute
        raise AttributeError(f"Attribute {name} not found in replayed interactions.")

    def __call__(self, *args: Tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        if self._current_call_index < len(self._recorded_calls):
            result = self._recorded_calls[self._current_call_index]
            self._current_call_index += 1
            return result[1]
        raise ValueError("No more recorded calls to replay.")

    async def __aenter__(self) -> Any:
        if "__aenter__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__aenter__"]
            if isinstance(result, list):
                return result.pop(0)
            return result
        raise AttributeError("No recorded __aenter__ result found.")

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if "__aexit__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__aexit__"]
            if isinstance(result, list):
                return result.pop(0)
            return result
        return False

    def __enter__(self) -> Any:
        if "__enter__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__enter__"]
            if isinstance(result, list):
                return result.pop(0)
            return result
        raise AttributeError("No recorded __enter__ result found.")

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        if "__exit__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__exit__"]
            if isinstance(result, list):
                return result.pop(0)
            return result
        return False

    async def __aiter__(self) -> Any:
        if "__aiter__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__aiter__"]
            if isinstance(result, list):
                value = result.pop(0)
                if isinstance(value, dict) and value.get("__type__") == "async_value":
                    return self
                return self
            return self
        raise AttributeError("No recorded __aiter__ result found.")

    def __aiter__(self) -> Any:
        if "__aiter__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__aiter__"]
            if isinstance(result, list):
                value = result.pop(0)
                if isinstance(value, dict) and value.get("__type__") == "async_value":
                    return self
                return self
            return self
        raise AttributeError("No recorded __aiter__ result found.")

    async def __anext__(self) -> Any:
        if "__anext__" in self._recorded_attribute_accesses:
            result = self._recorded_attribute_accesses["__anext__"]
            if isinstance(result, list):
                value = result.pop(0)
                if isinstance(value, dict) and value.get("__type__") == "async_value":
                    if isinstance(value["value"], StopAsyncIteration):
                        raise value["value"]
                    return value["value"]
                if isinstance(value, StopAsyncIteration):
                    raise value
                return value
            return result
        raise StopAsyncIteration
