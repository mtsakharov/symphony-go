"""RBAC domain exceptions."""


class RoleNotFoundError(Exception):
    """Raised when a role cannot be found."""


class PermissionNotFoundError(Exception):
    """Raised when a permission cannot be found."""


class RbacUserNotFoundError(Exception):
    """Raised when a user cannot be found for an RBAC operation."""


class RoleNameConflictError(Exception):
    """Raised when a role name already exists."""


class RolePermissionConflictError(Exception):
    """Raised when a permission is already assigned to a role."""


class RolePermissionNotFoundAssignmentError(Exception):
    """Raised when a role-permission assignment cannot be found."""


class UserRoleConflictError(Exception):
    """Raised when a role is already assigned to a user."""


class UserRoleNotFoundAssignmentError(Exception):
    """Raised when a user-role assignment cannot be found."""
