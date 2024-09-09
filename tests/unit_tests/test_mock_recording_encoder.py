import os

from mock_isolator.mock_recording_encoder import (
    DictMockRecordingEncoder,
    get_json_file_mock_interaction_recording_store,
)
from mock_isolator.recording_mock import BasicRecordingMocker, RecordingMock
from mock_isolator.replaying_mock import ReplayingMock


def test_record_and_replay_interactions():
    class TestResult:
        y: int

    class TestClass:
        def method1(self, x: int) -> int:
            return x + 1

        def method2(self, param: str) -> str:
            return f"{param}1"

        def method3(self) -> TestResult:
            result = TestResult()
            result.y = 2
            return result

    interaction_encoder = DictMockRecordingEncoder()
    recording_store = get_json_file_mock_interaction_recording_store()
    recording_mock = BasicRecordingMocker()
    recording_mock = RecordingMock(wrapped_item=TestClass(), mocker=recording_mock)

    # Record some interactions
    recording_mock.method1(1)
    recording_mock.method2(param="value")
    method3_result = recording_mock.method3()
    assert method3_result.y == 2

    # Verify the encoded interactions
    encoded_interactions = interaction_encoder.encode_recording_mock_interactions(
        recording_mock
    )
    expected_encoded_interactions = {
        "__type__": "RecordingMock",
        "recorded_attribute_accesses": {
            "method1": {
                "__repeat__": {
                    "__type__": "RecordingMock",
                    "recorded_calls": [
                        {
                            "__type__": "tuple",
                            "value": [
                                {
                                    "__type__": "tuple",
                                    "value": [{"__type__": "tuple", "value": [1]}, {}],
                                },
                                2,
                            ],
                        }
                    ],
                }
            },
            "method2": {
                "__repeat__": {
                    "__type__": "RecordingMock",
                    "recorded_calls": [
                        {
                            "__type__": "tuple",
                            "value": [
                                {
                                    "__type__": "tuple",
                                    "value": [
                                        {"__type__": "tuple", "value": []},
                                        {"param": "value"},
                                    ],
                                },
                                "value1",
                            ],
                        }
                    ],
                }
            },
            "method3": {
                "__repeat__": {
                    "__type__": "RecordingMock",
                    "recorded_calls": [
                        {
                            "__type__": "tuple",
                            "value": [
                                {
                                    "__type__": "tuple",
                                    "value": [{"__type__": "tuple", "value": []}, {}],
                                },
                                {
                                    "__type__": "RecordingMock",
                                    "recorded_attribute_accesses": {
                                        "y": {"__repeat__": 2}
                                    },
                                },
                            ],
                        }
                    ],
                }
            },
        },
    }
    assert encoded_interactions == expected_encoded_interactions

    # Serialize the interactions to a file
    base_filepath = os.path.dirname(os.path.abspath(__file__))
    output_file = (
        f"{base_filepath}/test_mock_recording_encoder_files/"
        "test_record_and_replay_interactions.json"
    )
    recording_store.store_recorded_mock_interactions_to_file(
        recording_mock, output_file
    )

    # Read from the file to create a replaying mock
    replaying_mock = recording_store.load_recorded_mock_interactions_from_file(
        output_file
    )

    # Replay the interactions
    assert replaying_mock.method1(1) == 2
    assert replaying_mock.method2(param="value") == "value1"
    method3_result = replaying_mock.method3()
    assert isinstance(method3_result, ReplayingMock)

    # Verify repeating results
    assert method3_result.y == 2
    assert method3_result.y == 2
