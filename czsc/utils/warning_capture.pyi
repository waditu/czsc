from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from _typeshed import Incomplete

@contextmanager
def capture_warnings() -> Generator[Incomplete, None, Incomplete]: ...
def execute_with_warning_capture(
    func: Callable, *args, return_as_string: bool = False, drop_duplicates: bool = True, **kwargs
) -> tuple[list[str], Any] | tuple[str, Any]: ...
