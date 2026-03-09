from _typeshed import Incomplete
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Callable

@contextmanager
def capture_warnings() -> Generator[Incomplete, None, Incomplete]: ...
def execute_with_warning_capture(func: Callable, *args, return_as_string: bool = False, drop_duplicates: bool = True, **kwargs) -> tuple[list[str], Any] | tuple[str, Any]: ...
