"""Domain/service-layer exceptions (no HTTP types)."""


class ServiceError(Exception):
    """Base exception for service-layer failures."""


class ValidationServiceError(ServiceError):
    """Invalid input or business rule violation."""


class ConflictServiceError(ServiceError):
    """Resource already exists or state conflict."""
