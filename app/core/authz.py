from typing import Iterable, Optional

from app.core.enums import RoleEnum
from app.models.user import User


ADMIN_ROLES = {RoleEnum.ADMIN, RoleEnum.SUPER_ADMIN}


def normalize_role(role: Optional[object]) -> Optional[RoleEnum]:
    """Normalize string/enum role values to RoleEnum."""
    if role is None:
        return None
    if isinstance(role, RoleEnum):
        return role
    try:
        return RoleEnum(str(role))
    except ValueError:
        return None


def normalize_roles(roles: Optional[Iterable[object]]) -> set[RoleEnum]:
    """Normalize a list of role values to a set of RoleEnum."""
    if not roles:
        return set()
    result: set[RoleEnum] = set()
    for role in roles:
        normalized = normalize_role(role)
        if normalized:
            result.add(normalized)
    return result


def is_admin_role(role: Optional[object]) -> bool:
    """Check whether role grants admin privileges."""
    normalized = normalize_role(role)
    return normalized in ADMIN_ROLES if normalized else False


def user_has_admin_role(user: User) -> bool:
    """Admin check based on role only (preferred over legacy is_admin flag)."""
    return is_admin_role(user.role)
