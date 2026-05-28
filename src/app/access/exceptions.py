"""Domain exceptions for access control resources."""


class RoleConflictError(Exception):
    """Raised when a role operation violates a uniqueness constraint."""


class RoleNotFoundError(Exception):
    """Raised when a role or requested role ids cannot be found."""


class PermissionConflictError(Exception):
    """Raised when a permission operation violates a uniqueness constraint."""


class PermissionNotFoundError(Exception):
    """Raised when a permission or requested permission ids cannot be found."""
