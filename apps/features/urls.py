from django.urls import path

from apps.features.views import FeatureFlagDetailView, FeatureFlagsView

urlpatterns = [
    path("", FeatureFlagsView.as_view(), name="feature-flags-list"),
    path("<str:flag_name>/", FeatureFlagDetailView.as_view(), name="feature-flag-detail"),
]
