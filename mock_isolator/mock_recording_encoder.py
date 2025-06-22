import json
import os
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Generic, List, Set, Tuple, TypeVar

from bson import ObjectId

from mock_isolator.recording_mock import RecordingMock
from mock_isolator.replaying_mock import ReplayingMock

EncodingType = TypeVar("EncodingType")
SerializedType = TypeVar("SerializedType", str, bytes)


class MockRecordingEncoder(ABC, Generic[EncodingType]):
    @abstractmethod
    def encode_recording_mock_interactions(
        self, mock: RecordingMock
    ) -> EncodingType | None:
        pass

    @abstractmethod
    def decode_recording_mock_interactions(
        self, encoded_interactions: EncodingType
    ) -> ReplayingMock:
        pass


class MockRecordingInteractionSerializer(ABC, Generic[EncodingType, SerializedType]):
    @abstractmethod
    def serialize_encoded_mock_interactions(
        self, encoded_interactions: EncodingType
    ) -> SerializedType:
        pass

    @abstractmethod
    def deserialize_encoded_mock_interactions(
        self, serialized_interactions: SerializedType
    ) -> EncodingType:
        pass


DictEncodingType = (
    bool
    | int
    | float
    | str
    | List["DictEncodingType"]
    | Dict[str, "DictEncodingType"]
    | None
)

DictMockRecordingEncoderValueType = (
    bool
    | int
    | float
    | str
    | Decimal
    | date
    | datetime
    | ObjectId
    | Tuple["DictMockRecordingEncoderValueType", ...]
    | List["DictMockRecordingEncoderValueType"]
    | frozenset["DictMockRecordingEncoderValueType"]
    | Set["DictMockRecordingEncoderValueType"]
    | Dict[str, "DictMockRecordingEncoderValueType"]
    | None
)

DictMockRecordingEncoderValueTypes = (
    bool,
    int,
    float,
    str,
    Decimal,
    date,
    datetime,
    ObjectId,
    tuple,
    list,
    frozenset,
    set,
    dict,
    type(None),
)


class DictMockRecordingEncoder(MockRecordingEncoder[DictEncodingType]):
    def encode_recording_mock_interactions(  # noqa: C901
        self, mock: RecordingMock
    ) -> DictEncodingType:
        if not mock.recorded_attribute_accesses and not mock.recorded_calls:
            return None

        def encode_item(  # noqa: C901
            item: Any,
            is_async: bool = False,
        ) -> DictEncodingType:
            if not isinstance(
                item, DictMockRecordingEncoderValueTypes + (RecordingMock,)
            ):
                raise TypeError(
                    f"Item of type {type(item)} is not a supported value type of "
                    "DictMockRecordingEncoder. Supported types are "
                    f"{DictMockRecordingEncoderValueType | RecordingMock}"
                )
            if isinstance(item, RecordingMock):
                serialized: Dict[str, DictEncodingType] = {
                    "__type__": "RecordingMock",
                }
                if item.recorded_attribute_accesses:
                    encoded_attribute_accesses = {
                        k: [encode_item(attr, is_async) for (attr, is_async) in zip(v, (i in item.recorded_async_attribute_access_indexes.get(k, set()) for i in range(len(v))))]
                        for k, v in item.recorded_attribute_accesses.items()
                    }
                    encoded_attribute_accesses_compacted = {
                        k: (
                            {"__repeat__": v[0]}
                            if len(v) > 0
                            and all(
                                v[0] == attr for attr in v
                            )
                            else v
                        )
                        for k, v in encoded_attribute_accesses.items()
                    }

                    serialized["recorded_attribute_accesses"] = encoded_attribute_accesses_compacted
                if item.recorded_calls:
                    serialized["recorded_calls"] = [
                        encode_item(call) for call in item.recorded_calls
                    ]
                return serialized
            elif isinstance(item, Decimal):
                return {"__type__": "Decimal", "value": str(item)}
            elif isinstance(item, datetime):
                return {"__type__": "datetime", "value": item.isoformat()}
            elif isinstance(item, date):
                return {"__type__": "date", "value": item.isoformat()}
            elif isinstance(item, ObjectId):
                return {"__type__": "ObjectId", "value": str(item)}
            elif isinstance(item, tuple):
                return {"__type__": "tuple", "value": [encode_item(i) for i in item]}
            elif isinstance(item, frozenset):
                return {
                    "__type__": "frozenset",
                    "value": [encode_item(i) for i in item],
                }
            elif isinstance(item, set):
                return {"__type__": "set", "value": [encode_item(i) for i in item]}
            elif isinstance(item, (int, str, float, bool, type(None))):
                if is_async:
                    return {"__type__": "async_value", "value": item}
                return item
            elif isinstance(item, dict):
                return {k: encode_item(v) for k, v in item.items()}
            elif isinstance(item, list) and not isinstance(item, (str, bytes)):
                return [encode_item(i) for i in item]
            else:
                return str(item)

        return encode_item(mock)

    def decode_recording_mock_interactions(  # noqa: C901
        self, encoded_interactions: DictEncodingType
    ) -> ReplayingMock:
        def decode_replaying_mock(item: DictEncodingType) -> ReplayingMock:
            if not isinstance(item, dict):
                raise TypeError(f"Expected dict for replaying mock, got {type(item)}")
            item_type = item["__type__"]
            if item_type != "RecordingMock":
                raise ValueError(
                    f'Expected __type__ set to "RecordingMock" instead of {item_type}'
                )
            recorded_attribute_accesses = item.get("recorded_attribute_accesses", {})
            if not isinstance(recorded_attribute_accesses, dict):
                raise TypeError(
                    "Expected dict for recorded_attribute_accesses, got "
                    f"{type(recorded_attribute_accesses)}"
                )
            recorded_calls = item.get("recorded_calls", [])
            if not isinstance(recorded_calls, list):
                raise TypeError(
                    f"Expected list for recorded_calls, got {type(recorded_calls)}"
                )
            decoded_recorded_attribute_accesses: Dict[
                str,
                List[DictMockRecordingEncoderValueType | ReplayingMock]
                | Dict[str, DictMockRecordingEncoderValueType | ReplayingMock],
            ] = {}
            for attribute_name, accesses in recorded_attribute_accesses.items():
                if not isinstance(attribute_name, str):
                    raise TypeError(
                        f"Expected str for recorded_attribute_accesses attribute_name, "
                        f"got {type(attribute_name)}"
                    )
                if isinstance(accesses, list):
                    decoded_recorded_attribute_accesses[attribute_name] = [
                        decode_item(attribute_value) for attribute_value in accesses
                    ]
                elif isinstance(accesses, dict):
                    repeated_value = decode_item(accesses["__repeat__"])
                    decoded_recorded_attribute_accesses[attribute_name] = {
                        "__repeat__": repeated_value
                    }
                else:
                    raise TypeError(
                        "Expected list or dict for recorded_attribute_accesses "
                        f"accesses, got {type(accesses)}"
                    )
            mock = ReplayingMock(
                recorded_attribute_accesses=decoded_recorded_attribute_accesses,
                recorded_calls=[
                    decode_item(call) for call in recorded_calls  # type: ignore
                ],
            )
            return mock

        def decode_item(  # noqa: C901
            item: DictEncodingType,
        ) -> DictMockRecordingEncoderValueType | ReplayingMock:
            if isinstance(item, dict):
                if "__type__" in item:
                    if item["__type__"] == "RecordingMock":
                        return decode_replaying_mock(item)
                    elif item["__type__"] == "Decimal":
                        return Decimal(str(item["value"]))
                    elif item["__type__"] == "datetime":
                        return datetime.fromisoformat(str(item["value"]))
                    elif item["__type__"] == "date":
                        return date.fromisoformat(str(item["value"]))
                    elif item["__type__"] == "ObjectId":
                        return ObjectId(str(item["value"]))
                    elif item["__type__"] in ["frozenset", "set", "tuple"]:
                        item_value = item["value"]
                        if not isinstance(item_value, list):
                            raise TypeError(
                                "Expected list for tuple item value, got "
                                f"{type(item_value)}"
                            )
                        if item["__type__"] == "frozenset":
                            return frozenset(
                                [decode_item(i) for i in item_value]  # type: ignore
                            )
                        if item["__type__"] == "set":
                            return {decode_item(i) for i in item_value}  # type: ignore
                        return tuple(decode_item(i) for i in item_value)  # type: ignore
                else:
                    return {k: decode_item(v) for k, v in item.items()}  # type: ignore
            elif isinstance(item, list):
                return [decode_item(i) for i in item]  # type: ignore
            else:
                return item

        return decode_replaying_mock(encoded_interactions)


class MockRecordingStore(Generic[EncodingType, SerializedType]):
    def __init__(
        self,
        interaction_encoder: MockRecordingEncoder[EncodingType],
        serializer: MockRecordingInteractionSerializer[EncodingType, SerializedType],
    ) -> None:
        self._interaction_encoder = interaction_encoder
        self._serializer: MockRecordingInteractionSerializer[
            EncodingType, SerializedType
        ] = serializer

    def store_recorded_mock_interactions_to_file(
        self, mock: RecordingMock, filepath: str
    ) -> None:
        encoded_interactions = (
            self._interaction_encoder.encode_recording_mock_interactions(mock)
        )
        if encoded_interactions is None:
            if os.path.exists(filepath):
                os.remove(filepath)
            return
        serialized_interactions = self._serializer.serialize_encoded_mock_interactions(
            encoded_interactions
        )
        with open(
            filepath, "wb" if isinstance(serialized_interactions, bytes) else "w"
        ) as file:
            file.write(serialized_interactions)

    def load_recorded_mock_interactions_from_file(self, filepath: str) -> ReplayingMock:
        if not os.path.exists(filepath):
            return ReplayingMock(recorded_attribute_accesses={}, recorded_calls=[])
        with open(filepath, "rb" if SerializedType is bytes else "r") as file:
            serialized_interactions = file.read()
        encoded_interactions = self._serializer.deserialize_encoded_mock_interactions(
            serialized_interactions
        )
        return self._interaction_encoder.decode_recording_mock_interactions(
            encoded_interactions
        )


class JsonMockRecordingInteractionSerializer(
    MockRecordingInteractionSerializer[DictEncodingType, str]
):
    def serialize_encoded_mock_interactions(
        self, encoded_interactions: DictEncodingType
    ) -> str:
        return json.dumps(encoded_interactions, indent=2)

    def deserialize_encoded_mock_interactions(
        self, serialized_interactions: str
    ) -> DictEncodingType:
        return json.loads(serialized_interactions)


def get_json_file_mock_interaction_recording_store() -> (
    MockRecordingStore[DictEncodingType, str]
):
    interaction_encoder = DictMockRecordingEncoder()
    serializer = JsonMockRecordingInteractionSerializer()
    return MockRecordingStore(interaction_encoder, serializer)
