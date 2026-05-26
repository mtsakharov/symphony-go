"""Users domain exceptions."""


class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""


class UserEmailConflictError(Exception):
    """Raised when an email already belongs to another user."""
