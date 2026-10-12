from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from listings.policies import require_active_actor
from listings.search.parsing import search_spec_from_dict, search_spec_to_dict, search_querystring
from listings.views import private_view
from .forms import SaveSearchForm, SearchNameForm
from .models import SavedSearch
from .services import save_search, rename_search, delete_search


@private_view
@login_required
@require_POST
def preference(request, search_id, enabled):
    from .services import set_notifications
    try:
        set_notifications(actor=request.user, search_id=search_id, enabled=enabled)
    except (ValidationError, TypeError, ValueError):
        messages.error(request, 'Kayıtlı arama geçersiz; bildirim açılamadı.')
    return redirect('notifications:index')


@private_view
@login_required
@require_GET
def inbox(request):
    from .models import NotificationDelivery
    from listings.favorites import require_private_actor
    from listings.queries import public_listings
    require_private_actor(request.user)
    page = Paginator(NotificationDelivery.objects.filter(recipient=request.user, archived_at=None), 12).get_page(request.GET.get('page'))
    rows = list(page)
    visible = {row.pk: row for row in public_listings().filter(pk__in=[row.listing_id for row in rows])}
    for row in rows:
        row.visible_listing = visible.get(row.listing_id)
    page.object_list = rows
    return render(request, 'notifications/inbox.html', {'page_obj': page})


@private_view
@login_required
@require_POST
def mark(request, delivery_id, archive=False):
    from .services import mark_notification
    mark_notification(actor=request.user, delivery_id=delivery_id, archive=archive)
    return redirect('notification_inbox')


@private_view
@login_required
@require_GET
def index(request):
    require_active_actor(actor=request.user)
    page = Paginator(SavedSearch.objects.filter(user=request.user).defer("spec"), 12).get_page(request.GET.get("page"))
    return render(request, "notifications/searches.html", {"page_obj": page})


@private_view
@login_required
@require_POST
def save(request):
    require_active_actor(actor=request.user)
    form = SaveSearchForm(request.POST)
    if form.is_valid():
        try:
            row, created = save_search(actor=request.user, name=form.cleaned_data["name"], payload=form.cleaned_data["spec"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Arama kaydedildi." if created else "Bu arama zaten kayıtlı; mevcut adı korundu.")
            return redirect("notifications:index")
    return render(request, "notifications/search_form.html", {"form": form, "title": "Aramayı kaydet"}, status=400)


@private_view
@login_required
@require_GET
def open_search(request, search_id):
    require_active_actor(actor=request.user)
    row = get_object_or_404(SavedSearch, pk=search_id, user=request.user)
    try:
        spec = search_spec_from_dict(row.spec)
        if search_spec_to_dict(spec) != row.spec:
            raise ValidationError("Kayıtlı arama canonical biçimi korunmalıdır.")
        query = search_querystring(spec)
    except (ValidationError, ValueError, TypeError):
        return render(request, "notifications/invalid_search.html", status=400)
    return redirect(reverse("listings:index") + ("?" + query if query else ""))


@private_view
@login_required
@require_http_methods(["GET", "POST"])
def rename(request, search_id):
    require_active_actor(actor=request.user)
    row = get_object_or_404(SavedSearch, pk=search_id, user=request.user)
    form = SearchNameForm(request.POST if request.method == "POST" else None, initial={"name": row.name})
    if request.method == "POST" and form.is_valid():
        rename_search(actor=request.user, search_id=row.pk, name=form.cleaned_data["name"])
        messages.success(request, "Arama adı güncellendi.")
        return redirect("notifications:index")
    return render(request, "notifications/search_form.html", {"form": form, "title": "Arama adını değiştir"},
                  status=400 if request.method == "POST" else 200)


@private_view
@login_required
@require_POST
def delete(request, search_id):
    delete_search(actor=request.user, search_id=search_id)
    messages.success(request, "Kayıtlı arama silindi.")
    return redirect("notifications:index")
