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


def test_record_and_replay_interactions_with_async_attributes():
    """Test that async attribute accesses with sets in recorded_async_attribute_access_indexes work correctly."""
    # Create a mock with some interactions
    mocker = BasicRecordingMocker()
    
    class TestClass:
        def __init__(self):
            self.attr1 = "value1"
            self.attr2 = "value2"
        def __call__(self, *args, **kwargs):
            return (args, kwargs)
    
    mock = RecordingMock(wrapped_item=TestClass(), mocker=mocker)
    
    # Simulate some regular attribute accesses by getting them (which will record them)
    _ = mock.attr1  # This will be recorded as an attribute access
    _ = mock.attr2  # This will be recorded as an attribute access
    
    # Simulate async attribute accesses (this would normally happen in real async code)
    # We need to manually set up the data structure that would be created by async attribute access
    mock.recorded_attribute_accesses["async_attr"] = ["async_value1", "async_value2"]
    mock.recorded_async_attribute_access_indexes["async_attr"] = {0, 1}  # Both are async
    
    # Simulate some calls
    mock(1, 2, kwarg="test")
    
    # Encode and decode
    encoder = DictMockRecordingEncoder()
    encoded = encoder.encode_recording_mock_interactions(mock)
    decoded = encoder.decode_recording_mock_interactions(encoded)
    
    # Verify the decoded mock has the expected structure
    assert isinstance(decoded, ReplayingMock)
    assert "attr1" in decoded._recorded_attribute_accesses
    assert "attr2" in decoded._recorded_attribute_accesses
    assert "async_attr" in decoded._recorded_attribute_accesses
    assert len(decoded._recorded_calls) == 1


def test_record_and_replay_interactions_with_mixed_async_attributes():
    """Test that mixed async and sync attribute accesses work correctly."""
    # Create a mock with some interactions
    mocker = BasicRecordingMocker()
    
    class TestClass:
        def __init__(self):
            self.attr1 = "value1"
            self.attr2 = "value2"
        def __call__(self, *args, **kwargs):
            return (args, kwargs)
    
    mock = RecordingMock(wrapped_item=TestClass(), mocker=mocker)
    
    # Simulate some regular attribute accesses by getting them
    _ = mock.attr1  # This will be recorded as an attribute access
    _ = mock.attr2  # This will be recorded as an attribute access
    
    # Simulate mixed attribute accesses where only some are async
    mock.recorded_attribute_accesses["mixed_attr"] = ["sync_value1", "async_value2", "sync_value3"]
    mock.recorded_async_attribute_access_indexes["mixed_attr"] = {1}  # Only index 1 is async
    
    # Encode and decode
    encoder = DictMockRecordingEncoder()
    encoded = encoder.encode_recording_mock_interactions(mock)
    decoded = encoder.decode_recording_mock_interactions(encoded)
    
    # Verify the decoded mock has the expected structure
    assert isinstance(decoded, ReplayingMock)
    assert "attr1" in decoded._recorded_attribute_accesses
    assert "attr2" in decoded._recorded_attribute_accesses
    assert "mixed_attr" in decoded._recorded_attribute_accesses


def test_record_and_replay_interactions_with_empty_async_indexes():
    """Test that empty async attribute access indexes work correctly."""
    # Create a mock with some interactions
    mocker = BasicRecordingMocker()
    
    class TestClass:
        def __init__(self):
            self.attr1 = "value1"
    
    mock = RecordingMock(wrapped_item=TestClass(), mocker=mocker)
    
    # Simulate some regular attribute accesses by getting them
    _ = mock.attr1  # This will be recorded as an attribute access
    
    # Simulate attribute accesses with no async indexes
    mock.recorded_attribute_accesses["sync_only_attr"] = ["value1", "value2"]
    # Don't add anything to recorded_async_attribute_access_indexes for this attribute
    
    # Encode and decode
    encoder = DictMockRecordingEncoder()
    encoded = encoder.encode_recording_mock_interactions(mock)
    decoded = encoder.decode_recording_mock_interactions(encoded)
    
    # Verify the decoded mock has the expected structure
    assert isinstance(decoded, ReplayingMock)
    assert "attr1" in decoded._recorded_attribute_accesses
    assert "sync_only_attr" in decoded._recorded_attribute_accesses
