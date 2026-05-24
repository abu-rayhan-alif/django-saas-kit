import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from django.core.asgi import get_asgi_application  # noqa: E402

# Django must be set up before importing Channels components.
django_asgi_app = get_asgi_application()

from apps.notifications.middleware import JWTAuthMiddlewareStack  # noqa: E402
from apps.notifications.routing import websocket_urlpatterns  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
