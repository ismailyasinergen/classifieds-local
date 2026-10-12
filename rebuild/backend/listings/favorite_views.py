from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .favorites import add_favorite, remove_favorite
from .models import Favorite
from .policies import require_active_actor
from .queries import public_listings
from .views import private_view


@private_view
@login_required
@require_GET
def index(request):
    require_active_actor(actor=request.user)
    page = Paginator(Favorite.objects.filter(user=request.user), 12).get_page(request.GET.get("page"))
    rows = list(page.object_list)
    visible = {item.pk: item for item in public_listings().filter(pk__in=[row.listing_id for row in rows])}
    for row in rows:
        row.visible_listing = visible.get(row.listing_id)
    page.object_list = rows
    return render(request, "listings/favorites.html", {"page_obj": page})


@private_view
@login_required
@require_POST
def add(request, listing_id):
    try:
        add_favorite(actor=request.user, listing_id=listing_id)
    except ValidationError as error:
        return render(request, "listings/favorite_error.html", {"error": error.messages[0]}, status=409)
    messages.success(request, "İlan favorilerinizde.")
    return redirect("listings:detail", listing_id=listing_id)


@private_view
@login_required
@require_POST
def remove(request, listing_id):
    remove_favorite(actor=request.user, listing_id=listing_id)
    messages.success(request, "Favori kaldırıldı.")
    return redirect("listings:favorites")
