"""
Identity domain module.

This module provides domain entities, value objects, and services
for user identity and authentication.
"""

from .value_objects import Email, UserId
from .services import AuthenticationService

__all__ = ['Email', 'UserId', 'AuthenticationService']
