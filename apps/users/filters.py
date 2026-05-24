import django_filters
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFilter(django_filters.FilterSet):
    """
    Filter set for GET /api/v1/users/list/.

    Supported query parameters
    --------------------------
    is_active            boolean — true or false
    date_joined_after    lower bound (inclusive) on join date (YYYY-MM-DD)
    date_joined_before   upper bound (inclusive) on join date (YYYY-MM-DD)
    """

    date_joined_after = django_filters.DateFilter(
        field_name="date_joined",
        lookup_expr="date__gte",
        label="Joined on or after (YYYY-MM-DD)",
    )
    date_joined_before = django_filters.DateFilter(
        field_name="date_joined",
        lookup_expr="date__lte",
        label="Joined on or before (YYYY-MM-DD)",
    )

    class Meta:
        model = User
        fields = {
            "is_active": ["exact"],
        }
