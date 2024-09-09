from typing import Tuple

import tests.unit_tests.test_module_mocking_isolator_module_2.file2 as f2
import tests.unit_tests.test_module_mocking_isolator_module_2.file3
from tests.unit_tests.test_module_mocking_isolator_module_2.file2 import (
    File2Class,
    do_file2_things,
)
from tests.unit_tests.test_module_mocking_isolator_module_2.file3 import File3Class

global_state: int = 0


def do_things_with_file2_class(f2_class: File2Class) -> int:
    f2_class.x = global_state
    return f2_class.x


def do_things_with_file3_class(f3_class: File3Class) -> int:
    f3_class.x = global_state
    return f3_class.x


class File1Class:
    def do_things_with_module_alias(self) -> Tuple[int, int]:
        return (
            do_things_with_file2_class(f2_class=f2.File2Class()),
            do_things_with_file2_class(f2_class=f2.do_file2_things()),
        )

    def do_things_with_imported_class(self) -> Tuple[int]:
        return (do_things_with_file2_class(f2_class=File2Class()),)

    def do_things_with_imported_function(self) -> Tuple[int]:
        return (do_things_with_file2_class(f2_class=do_file2_things()),)

    def do_things_with_imported_module(self) -> Tuple[int, int]:
        file3 = tests.unit_tests.test_module_mocking_isolator_module_2.file3
        return (
            do_things_with_file3_class(f3_class=file3.File3Class()),
            do_things_with_file3_class(f3_class=file3.do_file3_things()),
        )
