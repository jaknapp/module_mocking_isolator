import os
from contextlib import ExitStack

from mock_isolator.isolator import MockModuleMode, isolate_module_with_mocks


def _exercise_file1_in_mode_with_state(
    mode: MockModuleMode, global_state: int, expected_state: int
) -> None:
    with ExitStack() as stack:
        recording_filepath_prefix = os.path.join(
            os.path.dirname(__file__),
            "test_module_mocking_isolator_files/test_isolate_module_",
        )
        # Isolate file 1 from files 2 and 3
        isolate_module_with_mocks(
            exit_stack=stack,
            module_filepath="tests/unit_tests/test_module_mocking_isolator_module_1/file1.py",
            modules_to_mock=[
                "tests.unit_tests.test_module_mocking_isolator_module_2.file2",
                "tests.unit_tests.test_module_mocking_isolator_module_2.file3",
            ],
            mode=mode,
            recording_filepath_prefix=recording_filepath_prefix,
        )
        import tests.unit_tests.test_module_mocking_isolator_module_1.file1 as file1

        # Set the global state in file 1, then do operations in file 1 and file 2 that
        # are based on that state.
        # Increment the global state and expected state by 1 each step to make each
        # expected result a different number.

        f1 = file1.File1Class()
        file1.global_state = global_state
        assert f1.do_things_with_module_alias() == (expected_state, expected_state)
        file1.global_state = global_state + 1
        assert f1.do_things_with_imported_class() == (expected_state + 1,)
        file1.global_state = global_state + 2
        assert f1.do_things_with_imported_function() == (expected_state + 2,)
        file1.global_state = global_state + 3
        assert f1.do_things_with_imported_module() == (
            expected_state + 3,
            expected_state + 3,
        )


def test_isolate_module_with_mocks():
    """Test once in record mode, then verify it behaves the same in replay mode."""
    _exercise_file1_in_mode_with_state(
        mode=MockModuleMode.RECORD, global_state=1, expected_state=1
    )
    # Even though the global state has changed, the replay should still have the
    # expected results from the first run.
    _exercise_file1_in_mode_with_state(
        mode=MockModuleMode.REPLAY, global_state=2, expected_state=1
    )
