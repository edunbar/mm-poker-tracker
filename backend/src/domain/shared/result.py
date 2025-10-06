"""
Result type for representing success or failure of operations.

This module provides a type-safe way to handle operations that can fail
without using exceptions for business logic errors.
"""

from __future__ import annotations
from typing import Generic, TypeVar, Optional

T = TypeVar('T')


class Result(Generic[T]):
    """
    A Result type representing either success with a value or failure with an error.

    This pattern is inspired by Rust's Result and Scala's Either types, providing
    type-safe error handling without exceptions for business logic failures.

    Example:
        >>> # Success case
        >>> result = Result.success(42)
        >>> if result.is_success():
        >>>     print(result.value)  # 42
        >>>
        >>> # Failure case
        >>> result = Result.failure("Something went wrong")
        >>> if result.is_failure():
        >>>     print(result.error)  # "Something went wrong"
    """

    def __init__(self, success: bool, value: Optional[T] = None, error: Optional[str] = None):
        """
        Private constructor. Use Result.success() or Result.failure() instead.

        Args:
            success: Whether the operation was successful
            value: The success value (required if success=True)
            error: The error message (required if success=False)
        """
        self._success = success
        self._value = value
        self._error = error

    @classmethod
    def success(cls, value: T) -> Result[T]:
        """
        Create a successful Result with a value.

        Args:
            value: The success value

        Returns:
            Result indicating success with the given value

        Example:
            >>> result = Result.success(User(id="123", email="user@example.com"))
            >>> print(result.is_success())  # True
        """
        return cls(success=True, value=value)

    @classmethod
    def failure(cls, error: str) -> Result[T]:
        """
        Create a failed Result with an error message.

        Args:
            error: The error message describing why the operation failed

        Returns:
            Result indicating failure with the given error

        Example:
            >>> result = Result.failure("Email already registered")
            >>> print(result.is_failure())  # True
        """
        return cls(success=False, error=error)

    def is_success(self) -> bool:
        """
        Check if the Result represents a successful operation.

        Returns:
            True if successful, False if failed
        """
        return self._success

    def is_failure(self) -> bool:
        """
        Check if the Result represents a failed operation.

        Returns:
            True if failed, False if successful
        """
        return not self._success

    @property
    def value(self) -> T:
        """
        Get the success value.

        Returns:
            The value from a successful operation

        Raises:
            ValueError: If called on a failed Result

        Example:
            >>> result = Result.success(42)
            >>> print(result.value)  # 42
        """
        if not self._success:
            raise ValueError("Cannot get value from a failed Result. Check is_success() first.")
        return self._value  # type: ignore

    @property
    def error(self) -> str:
        """
        Get the error message.

        Returns:
            The error message from a failed operation

        Raises:
            ValueError: If called on a successful Result

        Example:
            >>> result = Result.failure("Invalid email")
            >>> print(result.error)  # "Invalid email"
        """
        if self._success:
            raise ValueError("Cannot get error from a successful Result. Check is_failure() first.")
        return self._error  # type: ignore

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self._success:
            return f"Result.success({self._value!r})"
        else:
            return f"Result.failure({self._error!r})"
