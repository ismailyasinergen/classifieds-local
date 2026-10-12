from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import Storefront
from accounts.storefront_forms import StorefrontForm, StorefrontEditForm, StorefrontVersionForm
from accounts.storefronts import (StorefrontConflict, change_storefront, create_storefront,
                                 public_storefronts, require_storefront_actor)
from listings.search.forms import SearchForm, bounded_page
from listings.search.parsing import search_querystring
from listings.search.queries import matching_public_listings, order_search_results


def manage_page(request, storefront, *, form=None, error=None, status=200):
    if form is None:
        form = StorefrontEditForm(initial={"name": storefront.draft_name, "intro": storefront.draft_intro,
            "edit_version": storefront.edit_version}) if storefront else StorefrontForm()
    return render(request, "accounts/storefront_manage.html", {
        "storefront": storefront, "form": form, "error": error,
        "public_available": bool(storefront and public_storefronts().filter(pk=storefront.pk).exists()),
    }, status=status)


@login_required
@require_GET
def manage(request):
    require_storefront_actor(request.user)
    return manage_page(request, Storefront.objects.filter(owner=request.user).first())


@login_required
@require_POST
def create(request):
    require_storefront_actor(request.user)
    form = StorefrontForm(request.POST)
    if form.is_valid():
        create_storefront(actor=request.user, **form.cleaned_data)
        messages.success(request, "Vitrin taslağınız oluşturuldu; henüz yayımlanmadı.")
        return redirect("storefronts:manage")
    return manage_page(request, None, form=form, status=400)


@login_required
@require_POST
def change(request, storefront_id, action):
    require_storefront_actor(request.user)
    storefront = get_object_or_404(Storefront, pk=storefront_id, owner=request.user)
    form = StorefrontEditForm(request.POST) if action == "save" else StorefrontVersionForm(request.POST)
    if not form.is_valid():
        return manage_page(request, storefront, form=form, status=400)
    data = dict(form.cleaned_data)
    data["expected_version"] = data.pop("edit_version")
    try:
        change_storefront(actor=request.user, storefront_id=storefront.pk, action=action, **data)
    except StorefrontConflict as error:
        return manage_page(request, storefront, error=error.messages[0], status=409)
    except ValidationError as error:
        return manage_page(request, storefront, error=" ".join(error.messages), status=400)
    messages.success(request, {"save": "Taslak kaydedildi; yayın değişmedi.",
        "publish": "Vitrin yayını güncellendi.", "unpublish": "Vitrin yayından kaldırıldı."}[action])
    return redirect("storefronts:manage")


def storefront_page(request, storefront, *, preview=False):
    form = SearchForm(request.GET)
    valid, page, previous_url, next_url = form.is_valid(), None, None, None
    url = reverse("storefronts:preview" if preview else "storefronts:public", args=[storefront.pk])
    if valid:
        try:
            spec = form.spec
            search_querystring(spec, page=9223372036854775807)
            queryset = order_search_results(matching_public_listings(spec=spec).filter(
                owner_id=storefront.owner_id), spec=spec)
            paginator = Paginator(queryset, 12)
            number = bounded_page(form.params.get("page"))
            page = paginator.get_page(paginator.num_pages if number is None else number)
            if page.has_previous():
                previous_url = url + "?" + search_querystring(spec, page=page.previous_page_number())
            if page.has_next():
                next_url = url + "?" + search_querystring(spec, page=page.next_page_number())
        except ValidationError as error:
            form.add_search_error(error)
            valid, page = False, None
    form.prepare_accessibility()
    return render(request, "accounts/storefront_page.html", {
        "storefront_name": storefront.draft_name if preview else storefront.published_name,
        "storefront_intro": storefront.draft_intro if preview else storefront.published_intro,
        "preview": preview, "search_form": form, "search_valid": valid,
        "search_spec": form.spec if valid else None, "page_obj": page,
        "search_url": url, "search_heading": "Bu vitrinde ara",
        "previous_url": previous_url, "next_url": next_url,
    })


@require_GET
def public(request, storefront_id):
    return storefront_page(request, get_object_or_404(public_storefronts(), pk=storefront_id))


@login_required
@require_GET
def preview(request, storefront_id):
    require_storefront_actor(request.user)
    return storefront_page(request, get_object_or_404(Storefront, pk=storefront_id, owner=request.user), preview=True)
