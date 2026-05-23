"""
Shared security defaults (SAAS-701).

Production/staging import these via ``config.settings.prod``.
"""

# API + bundled Swagger/ReDoc (inline assets). Tighten per-app in forks if needed.
DEFAULT_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

# HSTS — one year (only sent over HTTPS when SECURE_SSL_REDIRECT / TLS is active)
HSTS_SECONDS = 31_536_000
