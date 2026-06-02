"""Answer flow exceptions."""


class AnswerDependencyNotConfiguredError(RuntimeError):
    """Raised when an answer dependency has not been wired yet."""
