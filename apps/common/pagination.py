from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Default pagination for all list endpoints.

    Query parameters
    ----------------
    page       1-based page number (default: 1).
    page_size  Items per page (default: 20, max: 100).
               Pass ``page_size=0`` to disable pagination on a specific view
               by overriding ``pagination_class = None`` instead — this class
               always enforces a minimum of 1.

    Response envelope
    -----------------
    {
        "count":    <total items>,
        "next":     <URL | null>,
        "previous": <URL | null>,
        "results":  [...]
    }
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
