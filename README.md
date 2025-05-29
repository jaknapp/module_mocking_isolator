# Module Mocking Isolator

"Isolate dependencies with Record/Replay in Python"

## What is it?

The Module Mocking Isolator is used to isolate a module (a Python a file) from unwanted dependencies (imports) for the purposes of testing through the use of specialized mocks. The specialized mocks support a record and playback modes. This allows large scale mocking to be
feasible.

The mocks will replay the recorded values in the order that they were recorded in. In the case that all replayed values are the same, the ReplayMock will repeatedly return that value. The convenience of this is that if the unit under test is modified to access an attribute an additional time, a new recording is unnecessary.

## When and when not to use it?

Note, the best practice is to use dependency injection to allow tests to dependencies that are more conducive to tests. The Module Mocking Isolator is a tool to be used when refactoring to use dependency injection is not feasible, using real dependencies is too slow or not deterministic, other solutions such as pre-seed are not suitable, and mocking the dependencies by hand is too much work.

## How to add it to my test?

Call the function isolate_module_with_mocks by passing in the following information.

- `exit_stack` - The modules will be mocked for the lifetime of this ExitStack. In record mode, the recorded data will be written to file once the stack exits.
- `module_filepath` - the file path of the module (Python file) to isolate from its dependencies.
- `modules_to_mock` - the dependencies in the module to mock.
- `mode` - Whether to record or replay.
- `recording_filepath_prefix` - where to store the recorded data or replay recorded data. The data recorded for each mock will be stored in a separate file with a file path suffix equal to the module path of the module being isolated, followed by the imported name, and lastly followed by “.json”.
  - For example, the import `from mybig import dep as mybigdep` in the file
    `hello/world/module.py` will be recorded in the file
    `{recording_filepath_prefix}hello.world.mybigdep.json`.

See the example of how [test_module_mocking_isolator](tests/unit_tests/test_module_mocking_isolator.py) isolates [file1.py](tests/unit_tests/test_module_mocking_isolator_module_1/file1.py) from its dependencies from [file2](tests/unit_tests/test_module_mocking_isolator_module_2/file2.py) and [file3](tests/unit_tests/test_module_mocking_isolator_module_2/file3.py).

```python
with ExitStack() as stack:
    recording_filepath_prefix = os.path.join(
        os.path.dirname(__file__),
        "test_module_mocking_isolator_files/test_isolate_module_",
    )
    # Isolate file 1 from files 2 and 3
    isolate_module_with_mocks(
        exit_stack=stack,
        module_filepath="tests/app/mock/test_module_mocking_isolator_module_1/file1.py",
        modules_to_mock=[
            "tests.mock_isolator.test_module_mocking_isolator_module_2.file2",
            "tests.mock_isolator.test_module_mocking_isolator_module_2.file3",
        ],
        mode=mode, # MockIsolatorMode.REPLAY or MockIsolatorMode.RECORD
        recording_filepath_prefix=recording_filepath_prefix,
    )
```

Below is an example `conftests.py` to set the mode based on an environment variable or command line parameter.

```python
import os
import pytest
from mock_isolator.mock_recording_settings import MockRecordingSettings, MockIsolatorMode

# Configure mock mode based on environment variable
@pytest.hookimpl(tryfirst=True)  # Ensures this runs early
def pytest_configure(config):
    mode = os.getenv('MOCK_MODE', 'REPLAY').upper()  # Default to REPLAY mode

    if mode == 'RECORD':
        MockRecordingSettings.set_mode(MockIsolatorMode.RECORD)
    else:
        MockRecordingSettings.set_mode(MockIsolatorMode.REPLAY)

# Optionally, add a pytest command-line option for mode
def pytest_addoption(parser):
    parser.addoption("--mode", action="store", default=None, help="Set the mock mode: RECORD or REPLAY")

# If the user specifies --mode in the command line, override the environment variable
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    cmd_mode = config.getoption("--mode")
    if cmd_mode:
        mode = cmd_mode.upper()
    else:
        mode = os.getenv('MOCK_MODE', 'REPLAY').upper()

    if mode == 'RECORD':
        MockRecordingSettings.set_mode(MockIsolatorMode.RECORD)
    else:
        MockRecordingSettings.set_mode(MockIsolatorMode.REPLAY)
```

For running tests in a hot-reload REPL, the mode can be set directly:

```python
from mock_isolator.mock_recording_settings import MockRecordingSettings, MockIsolatorMode

# Set to Record mode
MockRecordingSettings.set_mode(MockIsolatorMode.RECORD)

# Or set to Replay mode
MockRecordingSettings.set_mode(MockIsolatorMode.REPLAY)
```

Be sure to pass the mode based on the setting in the tests:

```python
isolate_module_with_mocks(..., mode=MockRecordingSettings.get_mode(), ...)
```

## What are the limitations?

### Recorded mocks often cannot be used alongside real components

For example, if a mocked module returns data that includes a randomly generated database model ID and the test is in record mode, this ID will be saved in the mock recording file. When the test is run again, the test will likely create a new model object with a different ID that doesn’t match the recorded ID. This can lead to inconsistencies between the recorded values and other values used throughout the system. To address this, you would have to either reduce the scope of the test to the module that is being isolated or mock other modules as well.

### The mocks may not support every kind of data or usage

Creating a mock that behaves exactly like the real thing can be a challenge. For example, if the code checks the mock’s type, it will be either a RecordingMock or ReplayingMock and not the original type that the mock is pretending to be.

If you run into issues with the mocks themselves, you may have to update `RecordingMock` / `ReplayingMock` to be a better pretender or update `DictMockRecordingEncoder.encode_recording_mock_interactions` / `decode_recording_mock_interactions` .

### The ReplayingMocks don’t check argument values

Currently, there is no validation that the inputs to the mocks match the inputs from when the mock was recorded. The mocks simply replay values in the order they originally were recorded in. This could potentially lead to unexpected behavior if the result would be meaningfully different due to different arguments.

### Is this is a replacement for VCR tests?

Not in many cases. The VCR tests have the benefit of ensuring that the network request matches the recorded network request. The ReplayingMocks don’t verify that the arguments are equivalent to the ones used during the recording.

VCR also works at a lower level of the stack, which means that you could do a code refactor and still re-use the existing VCRs but, depending on the refactor, you might have to redo the mock recordings.

## Future work

### Interoperability of mocks and live components

To achieve the ideal ability of isolating only the parts of the unit under test that are unwanted, we can add the ability to have a data structure of replacement values that allow the mocked dependencies to use the live values in the test. For the example of company ID, an input to `isolate_module_with_mocks` can include the live company ID in the test and the `ReplayingMock` can swap any instances of the recorded company ID with the live company ID.

### More precise diffs

Similarly to the above, replacement values would help in the reverse direction. That is to say the replacements data structure should be a one to one mapping where you can go from key to value or value to key. Currently, when you record a new run of the test, all previously generated unique IDs are replaced with new ones. This can lead to a large diff of things that didn’t make a semantic difference. Instead, we can replace the new values with the previously recorded values so that only real changes are highlighted in the diff.

### Verifying passed arguments

Using replacement values, we could verify that the passed arguments match the expected values. For example, if an invocation of the function foo was recorded as `foo(company="company123")` and we now see `foo(entity="entity123")` or `foo(company="entity123")`, we should fail the test instead of returning the recorded values from `foo`.

### Support Interactive mode

In some scenarios, it might make sense to support an interactive mode that stops and waits for input whenever a mocked dependency is called. This value is then recorded. This could be helpful for cases where the real dependency doesn’t exist yet. In this case, the mock would serve as a self documenting contract of how the dependency should behave.

### Generating DTOs and code refactor

In the beginning of this doc it mentions, “the best practice is to use dependency injection to allow tests to dependencies that are more conducive to tests”. An automated utility could take the mock recordings and output Python code that instantiates DTOs that are populated with this data. The unit under test could be modified to allow dependency injection that uses these DTOs instead of direct dependencies on other unwanted modules. Going forward, the DTOs could be incrementally updated directly instead of having to rely on this mocking framework and maintain mock recordings.

In some cases, if the recorded values are not already DTOs, the framework could define the DTOs in Python. The dependencies could then be updated to return these DTOs or a thin layer can be added around the dependency to convert to DTOs.

## Contributing

Contributions are welcome!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
