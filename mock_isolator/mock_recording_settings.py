from mock_isolator.isolator import MockModuleMode


class MockRecordingSettings:
    """
    Controls the mock recording/replay setting. Usage with hot tests:

    >>> from mock_isolator.isolator import MockModuleMode
    >>> MockRecordingSettings.set_mode(MockModuleMode.RECORD)
    >>> test(...)
    >>> MockRecordingSettings.set_mode(MockModuleMode.REPLAY)
    >>> test(...)
    """

    _mode = MockModuleMode.REPLAY

    @classmethod
    def set_mode(cls, mode: MockModuleMode):
        cls._mode = mode

    @classmethod
    def get_mode(cls) -> MockModuleMode:
        return cls._mode
