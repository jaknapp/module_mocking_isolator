from typing import Any, Tuple


class ReplayingMock:
    """
    Replays a recording (ie. from a RecordingMock) such that the originally wrapped
    item is no longer needed.
    """

    def __init__(
        self,
        recorded_attribute_accesses: dict[str, list[Any] | dict[str, Any] | Any],
        recorded_calls: list[Tuple[Tuple[Any, ...], dict[str, Any]]],
    ):
        self._recorded_attribute_accesses = recorded_attribute_accesses
        self._recorded_calls = recorded_calls
        self._current_call_index = 0

    def __getattribute__(self, name: str) -> Any:
        if name in [
            "_recorded_attribute_accesses",
            "_recorded_calls",
            "_current_call_index",
            "__class__",
            "__dict__",
            "__getattribute__",
        ]:
            return object.__getattribute__(self, name)
        if name in self._recorded_attribute_accesses:
            attribute = self._recorded_attribute_accesses[name]
            if isinstance(attribute, dict) and "__repeat__" in attribute:
                return attribute["__repeat__"]
            if isinstance(attribute, list):
                return attribute.pop(0)
            return attribute
        raise AttributeError(f"Attribute {name} not found in replayed interactions.")

    def __call__(self, *args: Tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        if self._current_call_index < len(self._recorded_calls):
            result = self._recorded_calls[self._current_call_index]
            self._current_call_index += 1
            return result[1]
        raise ValueError("No more recorded calls to replay.")
