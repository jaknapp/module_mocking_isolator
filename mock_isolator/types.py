from enum import Enum


class MockIsolatorMode(Enum):
    RECORD = "RECORD"
    REPLAY = "REPLAY"
    INTERACTIVE = "INTERACTIVE"