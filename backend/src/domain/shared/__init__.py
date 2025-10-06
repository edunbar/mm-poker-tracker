"""
Shared domain interfaces and utilities.

This module contains domain interfaces that are used across multiple bounded contexts.
"""

from .password_hasher import PasswordHasher, PasswordHashingError
from .result import Result

__all__ = ['PasswordHasher', 'PasswordHashingError', 'Result']
