from mock_isolator.types import MockIsolatorMode


class MockRecordingSettings:
    """
    Controls the mock recording/replay setting. Usage with hot tests:

    >>> from mock_isolator.isolator import MockIsolatorMode
    >>> MockRecordingSettings.set_mode(MockIsolatorMode.RECORD)
    >>> test(...)
    >>> MockRecordingSettings.set_mode(MockIsolatorMode.REPLAY)
    >>> test(...)
    """

    _mode = MockIsolatorMode.REPLAY

    @classmethod
    def set_mode(cls, mode: MockIsolatorMode):
        cls._mode = mode

    @classmethod
    def get_mode(cls) -> MockIsolatorMode:
        return cls._mode
