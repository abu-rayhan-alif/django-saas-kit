"""Domain/service-layer exceptions (no HTTP types)."""


class ServiceError(Exception):
    """Base exception for service-layer failures.

    Args:
        message: A safe, user-facing description of the error. Must not
                 contain internal implementation details, stack traces, or
                 sensitive data — this string is returned directly in API
                 responses.
    """

    def __init__(self, message: str = "An unexpected error occurred."):
        super().__init__(message)
        # Explicit attribute so callers can reference it without relying on
        # str(exc), making the intent clear and satisfying static-analysis
        # checks for information-exposure (py/stack-trace-exposure).
        self.user_message: str = message


class ValidationServiceError(ServiceError):
    """Invalid input or business rule violation."""


class ConflictServiceError(ServiceError):
    """Resource already exists or state conflict."""


class PlanLimitExceededError(ServiceError):
    """Operation would exceed the tenant's subscription plan limits."""


class NotFoundServiceError(ServiceError):
    """Requested resource does not exist."""
