from django.urls import path

from apps.invitations.views import (
    InvitationAcceptView,
    InvitationDetailView,
    InvitationRevokeView,
    TenantInvitationListCreateView,
)

urlpatterns = [
    path("", TenantInvitationListCreateView.as_view(), name="invitation-list-create"),
    path("<str:token>/", InvitationDetailView.as_view(), name="invitation-detail"),
    path("<str:token>/accept/", InvitationAcceptView.as_view(), name="invitation-accept"),
    path("<uuid:invitation_id>/revoke/", InvitationRevokeView.as_view(), name="invitation-revoke"),
]
