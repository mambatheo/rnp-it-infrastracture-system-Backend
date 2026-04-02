from django.db import connection
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FlexiblePageNumberPagination(PageNumberPagination):
    """
    Pagination with fast approximate counts for large tables.

    For tables with > 10,000 rows we use PostgreSQL's statistics-based
    estimate (pg_class.reltuples) instead of COUNT(*).  This is nearly
    instant regardless of table size.  For small tables we fall back to
    an exact count so the UI is always accurate when it matters.
    """
    page_size              = 15
    page_size_query_param  = "page_size"
    max_page_size          = 500   # cap runaway requests

    # Threshold above which we switch to the approximate count
    APPROX_COUNT_THRESHOLD = 10_000

    def _approx_count(self, queryset):
        """
        Return PostgreSQL's estimated row count for the table that backs
        *queryset*, or None if we cannot determine it (non-Postgres DB,
        filtered queryset, etc.).
        """
        # Only use the estimate when there are no WHERE filters applied
        # (i.e. the queryset is unfiltered — checking via query.where)
        if queryset.query.where:
            return None

        try:
            model    = queryset.model
            db_table = connection.ops.quote_name(model._meta.db_table)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
                    [model._meta.db_table],
                )
                row = cursor.fetchone()
            if row and row[0] >= 0:
                return int(row[0])
        except Exception:
            pass
        return None

    def paginate_queryset(self, queryset, request, view=None):
        # Store the queryset so get_paginated_response can inspect it
        self._queryset = queryset
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        # Try fast path first
        approx = self._approx_count(self._queryset)
        if approx is not None and approx > self.APPROX_COUNT_THRESHOLD:
            count = approx
        else:
            count = self.page.paginator.count   # exact — already computed by DRF

        return Response({
            "count":    count,
            "next":     self.get_next_link(),
            "previous": self.get_previous_link(),
            "results":  data,
        })

