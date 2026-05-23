from apps.common.views import HealthCheckView
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/rbac/", include("apps.rbac.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/", include("apps.common.urls")),
    # OpenAPI schema & documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
