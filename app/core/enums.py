"""
Enums for the application.
"""
from enum import Enum


class RoleEnum(str, Enum):
    """User roles in the system."""
    ADMIN = "ROLE_ADMIN"
    TEACHER = "ROLE_TEACHER"
    STUDENT = "ROLE_USER"
    PRINCIPAL = "ROLE_PRINCIPAL"
    SUPER_ADMIN = "ROLE_SUPER_ADMIN"


class GenderEnum(str, Enum):
    """Gender options for users."""
    MALE = "MALE"
    FEMALE = "FEMALE"


class EnvironmentEnum(str, Enum):
    """Environment types."""
    development = "development"
    staging = "staging"
    production = "production"


class UserTypeEnum(str, Enum):
    """User type classification."""
    TELEGRAM = "TELEGRAM"  # User authenticated via Telegram
    EXTERNAL = "EXTERNAL"  # User from external app (e.g., Katalis)
    INTERNAL = "INTERNAL"  # User created internally (Teacher, Admin)
