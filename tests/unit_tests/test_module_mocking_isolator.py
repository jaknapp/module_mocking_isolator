import os
from contextlib import ExitStack

from mock_isolator.isolator import isolate_module_with_mocks, isolate_dependencies_with_mocks
from mock_isolator.types import MockIsolatorMode


def _exercise_file1_in_mode_with_state(
    mode: MockIsolatorMode, global_state: int, expected_state: int
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
        mode=MockIsolatorMode.RECORD, global_state=1, expected_state=1
    )
    # Even though the global state has changed, the replay should still have the
    # expected results from the first run.
    _exercise_file1_in_mode_with_state(
        mode=MockIsolatorMode.REPLAY, global_state=2, expected_state=1
    )


def test_isolate_dependencies_with_mocks():
    """Test once in record mode, then verify it behaves the same in replay mode."""
    # Create a simple class that we'll use as a dependency
    class Calculator:
        def add(self, x: int, y: int) -> int:
            return x + y
        
        def multiply(self, x: int, y: int) -> int:
            return x * y

    # Create a function that uses our dependency
    def process_numbers(calc: Calculator, x: int, y: int) -> tuple[int, int]:
        return calc.add(x, y), calc.multiply(x, y)

    # First run in record mode
    with ExitStack() as stack:
        recording_filepath_prefix = os.path.join(
            os.path.dirname(__file__),
            "test_module_mocking_isolator_files/test_isolate_dependencies_",
        )
        
        # Create real dependencies
        calculator = Calculator()
        
        # Get mocked dependencies in record mode
        mocked_deps = isolate_dependencies_with_mocks(
            exit_stack=stack,
            dependencies=[calculator],
            dependency_names=["calculator"],
            mode=MockIsolatorMode.RECORD,
            recording_filepath_prefix=recording_filepath_prefix,
        )
        
        # Use the mocked dependencies
        result = process_numbers(mocked_deps["calculator"], 2, 3)
        assert result == (5, 6)  # 2+3=5, 2*3=6

    # Now run in replay mode
    with ExitStack() as stack:
        # Get mocked dependencies in replay mode
        mocked_deps = isolate_dependencies_with_mocks(
            exit_stack=stack,
            dependencies=[Calculator()],  # This instance won't be used in replay mode
            dependency_names=["calculator"],
            mode=MockIsolatorMode.REPLAY,
            recording_filepath_prefix=recording_filepath_prefix,
        )
        
        # Even with different inputs, should still get recorded results
        result = process_numbers(mocked_deps["calculator"], 4, 5)
        assert result == (5, 6)  # Still matches record mode results