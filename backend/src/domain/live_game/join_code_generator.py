"""
Join code generation utilities for live games.

This module provides functions to generate unique 4-character join codes
that are easy to read and type, avoiding confusing characters like O/0 and I/1.
"""

import random
import string
from typing import Callable

from .value_objects import JoinCode


def generate_join_code() -> str:
    """
    Generate a random 4-character join code.

    The code uses uppercase letters and digits, but excludes characters
    that are commonly confused:
    - O (letter) and 0 (zero)
    - I (letter) and 1 (one)
    - L (letter, looks like 1)

    Returns:
        4-character string suitable for a join code

    Example:
        >>> code = generate_join_code()
        >>> len(code)
        4
        >>> code.isupper()
        True
        >>> 'O' not in code and '0' not in code
        True
    """
    # Remove O, I, 0, 1, L to avoid confusion
    chars = ''.join(c for c in string.ascii_uppercase + string.digits
                    if c not in 'OI01L')
    return ''.join(random.choices(chars, k=4))


def create_unique_join_code(check_exists_fn: Callable[[str], bool]) -> JoinCode:
    """
    Generate a unique join code by checking against existing codes.

    This function generates join codes and validates them against the
    database until a unique code is found.

    Args:
        check_exists_fn: Function that takes a code string and returns
                        True if it already exists, False otherwise

    Returns:
        Unique JoinCode value object

    Raises:
        RuntimeError: If unable to generate unique code after 10 attempts
                     (extremely rare with 4-char alphanumeric space)

    Example:
        >>> def check_exists(code: str) -> bool:
        ...     return code in ["A3X7", "B9K2"]
        ...
        >>> unique_code = create_unique_join_code(check_exists)
        >>> unique_code.value not in ["A3X7", "B9K2"]
        True
    """
    max_attempts = 10
    for _ in range(max_attempts):
        code_str = generate_join_code()
        if not check_exists_fn(code_str):
            return JoinCode(code_str)

    # This should be extremely rare - with 4 characters and ~31 allowed chars,
    # there are 31^4 = 923,521 possible codes
    raise RuntimeError("Failed to generate unique join code after 10 attempts")
