from django.db import connection
from .models import PublicationBoundary


def next_publication_boundary():
    """Call last in an atomic writer, after Listing/account locks; held until commit."""
    if not connection.in_atomic_block:
        raise RuntimeError('boundary_requires_transaction')
    PublicationBoundary.objects.get_or_create(pk=1)
    row = PublicationBoundary.objects.select_for_update().get(pk=1)
    row.value += 1
    row.save(update_fields=['value'])
    return row.value
