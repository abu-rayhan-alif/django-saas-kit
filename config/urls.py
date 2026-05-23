from apps.common.exceptions import handler404 as _h404
from apps.common.exceptions import handler500 as _h500
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
    # v1 API
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/tenants/", include("apps.tenants.urls")),
    path("api/v1/rbac/", include("apps.rbac.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.common.urls")),
    # OpenAPI schema & interactive docs (unversioned — serve all API versions)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# JSON error pages for non-DRF views
handler404 = _h404
handler500 = _h500
