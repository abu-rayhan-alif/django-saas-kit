from django.urls import path

from apps.rbac.views import AssignRoleView, RevokeRoleView, TenantRoleListView

urlpatterns = [
    path("<uuid:tenant_id>/roles/", TenantRoleListView.as_view(), name="rbac-role-list"),
    path("<uuid:tenant_id>/roles/assign/", AssignRoleView.as_view(), name="rbac-role-assign"),
    path("<uuid:tenant_id>/roles/revoke/", RevokeRoleView.as_view(), name="rbac-role-revoke"),
]
