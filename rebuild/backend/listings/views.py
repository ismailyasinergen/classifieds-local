import json
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from accounts.rate_limits import ActionRateLimited
from media.models import MediaAsset, RevisionImage
from media.services import attach_image, remove_image, retry_image
from moderation.policies import require_reviewer
from .forms import CategoryForm, DraftForm, UploadForm, add_service_errors
from .models import Favorite, Listing, ListingRevision
from .policies import require_active_actor, require_owner
from .publication import submit_revision, withdraw_revision
from .queries import public_listings
from .search.forms import SearchForm, bounded_page
from .search.parsing import search_querystring, search_spec_to_dict
from .search.queries import matching_public_listings, order_search_results
from .services import InvalidRevisionState, StaleEditVersion, create_listing_draft, start_revision, update_draft


def private(response):
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def private_view(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        return private(view(*args, **kwargs))
    return wrapped


def revision_for(request, revision_id, *, reviewer=False):
    require_active_actor(actor=request.user)
    revision = get_object_or_404(
        ListingRevision.objects.select_related("listing", "category", "attribute_schema", "moderation_decision")
        .prefetch_related(Prefetch("images", queryset=RevisionImage.objects.select_related("asset"))), pk=revision_id)
    if revision.listing.owner_id != request.user.pk:
        if not reviewer:
            raise PermissionDenied()
        require_reviewer(actor=request.user)
    return revision


def attributes_for(revision):
    result = []
    for name, rule in revision.attribute_schema.definition["fields"].items():
        if name not in revision.attributes:
            continue
        value = revision.attributes[name]
        if type(value) is bool:
            value = "Evet" if value else "Hayır"
        result.append((rule.get("label", name.replace("_", " ").capitalize()), value, rule.get("unit", "")))
    return result


def edit_page(request, revision, *, form=None, upload_form=None, status=200, step=None):
    step = step or ("details" if request.GET.get("step") == "details" else "photos")
    return private(render(request, "listings/edit.html", {
        "revision": revision, "step": step, "form": form if form is not None else DraftForm(revision=revision),
        "upload_form": upload_form if upload_form is not None else UploadForm(),
        "images": revision.images.all(), "pending": any(link.asset.state == "pending" for link in revision.images.all()),
    }, status=status))


@require_GET
def index(request):
    form = SearchForm(request.GET)
    page, previous_url, next_url = None, None, None
    sponsored = []
    valid = form.is_valid()
    if valid:
        spec = form.spec
        try:
            # Reserve the largest possible page spelling before any Listing COUNT.
            search_querystring(spec, page=9223372036854775807)
            queryset = order_search_results(matching_public_listings(spec=spec), spec=spec)
            paginator = Paginator(queryset, 12)
            requested_page = bounded_page(form.params.get("page"))
            page = paginator.get_page(paginator.num_pages if requested_page is None else requested_page)
            if page.has_previous():
                previous_url = "?" + search_querystring(spec, page=page.previous_page_number())
            if page.has_next():
                next_url = "?" + search_querystring(spec, page=page.next_page_number())
        except ValidationError as error:
            form.add_search_error(error)
            valid, page = False, None
    if valid and page is not None and page.number == 1:
        from django.conf import settings
        if settings.PROMOTIONS_DEMO_ENABLED and settings.DEPLOYMENT_ENVIRONMENT == 'developer':
            from promotions.services import sponsored_listings
            sponsored = sponsored_listings(spec=form.spec)
    form.prepare_accessibility()
    from notifications.forms import SaveSearchForm
    save_form = SaveSearchForm(initial={"spec": json.dumps(search_spec_to_dict(form.spec), ensure_ascii=False)}) if valid else None
    return render(request, "listings/index.html", {
        "save_search_form": save_form, "sponsored": sponsored,
        "search_form": form, "search_valid": valid, "search_spec": form.spec if valid else None,
        "page_obj": page, "selected_category": str(form.spec.category_id)
        if form.spec is not None and form.spec.category_id is not None else "",
        "categories": form.categories, "previous_url": previous_url, "next_url": next_url,
    })


@require_GET
@private_view
def detail(request, listing_id):
    from accounts.storefronts import public_storefronts
    listing = get_object_or_404(public_listings(), pk=listing_id)
    revision = listing.public_revision
    return render(request, "listings/detail.html", {
        "listing": listing, "revision": revision, "attributes": attributes_for(revision),
        "seller_storefront": public_storefronts().filter(owner_id=listing.owner_id).only("id").first(),
        "images": revision.images.all(),
        "is_favorite": request.user.is_authenticated and Favorite.objects.filter(user=request.user, listing=listing).exists()})


@login_required
@require_GET
@private_view
def dashboard(request):
    require_active_actor(actor=request.user)
    visible_ids = set(public_listings().filter(owner=request.user).values_list("pk", flat=True))
    rows = []
    queryset = Listing.objects.filter(owner=request.user).select_related("public_revision").prefetch_related(
        Prefetch("revisions", queryset=ListingRevision.objects.select_related("moderation_decision").order_by("-created_at", "-pk")))
    page = Paginator(queryset, 12).get_page(request.GET.get("page"))
    for listing in page:
        latest = next(iter(listing.revisions.all()), None)
        rows.append({"listing": listing, "latest": latest, "visible": listing.pk in visible_ids})
    from django.conf import settings
    return render(request, "listings/dashboard.html", {"rows": rows, "page_obj": page,
        "promotions_demo": settings.PROMOTIONS_DEMO_ENABLED and settings.DEPLOYMENT_ENVIRONMENT == 'developer'})


@login_required
@require_http_methods(["GET", "POST"])
@private_view
def create(request):
    require_active_actor(actor=request.user)
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            revision = create_listing_draft(actor=request.user, category_id=form.cleaned_data["category"], content={})
        except ObjectDoesNotExist:
            raise Http404() from None
        except ActionRateLimited as error:
            form.add_error(None, error)
            response = render(request, "listings/create.html", {"form": form}, status=429)
            response["Retry-After"] = str(error.retry_after)
            return response
        except ValidationError as error:
            add_service_errors(form, error)
        else:
            return redirect("listings:edit", revision_id=revision.pk)
    return render(request, "listings/create.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
@private_view
def edit(request, revision_id):
    revision = revision_for(request, revision_id)
    if revision.status != "draft":
        return private(render(request, "listings/conflict.html", {"revision": revision,
                       "error": "Bu sürüm artık taslak değil. Özel önizlemeden durumunu kontrol edin."}, status=409))
    form = DraftForm(request.POST if request.method == "POST" else None, revision=revision)
    if request.method == "POST" and form.is_valid():
        try:
            update_draft(actor=request.user, revision_id=revision.pk,
                         expected_version=form.cleaned_data["edit_version"], content=form.content)
        except (StaleEditVersion, InvalidRevisionState) as error:
            add_service_errors(form, error)
            return edit_page(request, revision, form=form, status=409, step="details")
        except ValidationError as error:
            add_service_errors(form, error)
        else:
            messages.success(request, "Taslağın kaydedildi.")
            if request.POST.get("save_exit"):
                return redirect("listings:dashboard")
            return redirect("listings:preview", revision_id=revision.pk)
    return edit_page(request, revision, form=form)


@login_required
@require_GET
@private_view
def preview(request, revision_id):
    revision = revision_for(request, revision_id, reviewer=True)
    return render(request, "listings/preview.html", {"revision": revision, "images": revision.images.all(),
                  "attributes": attributes_for(revision), "is_owner": revision.listing.owner_id == request.user.pk})


@login_required
@require_POST
@private_view
def submit(request, revision_id):
    revision = revision_for(request, revision_id)
    try:
        submit_revision(actor=request.user, revision_id=revision.pk)
    except InvalidRevisionState as error:
        return render(request, "listings/conflict.html", {"revision": revision, "error": error.messages[0]}, status=409)
    except ValidationError as error:
        return render(request, "listings/preview.html", {"revision": revision, "images": revision.images.all(),
                      "attributes": attributes_for(revision), "is_owner": True, "errors": error.messages}, status=400)
    messages.success(request, "İlanın incelemeye gönderildi.")
    return redirect("listings:dashboard")


@login_required
@require_POST
@private_view
def withdraw(request, revision_id):
    revision = revision_for(request, revision_id)
    try:
        withdraw_revision(actor=request.user, revision_id=revision.pk)
    except ValidationError as error:
        return render(request, "listings/conflict.html", {"revision": revision, "error": error.messages[0]}, status=409)
    messages.success(request, "İnceleme isteği geri çekildi. Yeni taslak oluşturabilirsin.")
    return redirect("listings:dashboard")


@login_required
@require_POST
@private_view
def restart(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    require_owner(actor=request.user, listing=listing)
    try:
        revision = start_revision(actor=request.user, listing_id=listing.pk)
    except ValidationError as error:
        return render(request, "listings/conflict.html", {"error": error.messages[0]}, status=409)
    return redirect("listings:edit", revision_id=revision.pk)


@login_required
@require_POST
@private_view
@transaction.non_atomic_requests
def image_attach(request, revision_id):
    # Validate the form first; attach_image owns its durable transaction and file compensation.
    revision = revision_for(request, revision_id)
    form = UploadForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            attach_image(actor=request.user, revision_id=revision.pk, uploaded_file=form.cleaned_data["image"])
        except InvalidRevisionState as error:
            add_service_errors(form, error)
            return edit_page(request, revision, upload_form=form, status=409)
        except ValidationError as error:
            add_service_errors(form, error)
        else:
            return redirect("listings:edit", revision_id=revision.pk)
    return edit_page(request, revision, upload_form=form)


@login_required
@require_POST
@private_view
def image_remove(request, revision_id, asset_id):
    revision = revision_for(request, revision_id)
    try:
        remove_image(actor=request.user, revision_id=revision.pk, asset_id=asset_id)
    except ObjectDoesNotExist:
        raise Http404() from None
    except ValidationError as error:
        return render(request, "listings/conflict.html", {"revision": revision, "error": error.messages[0]}, status=409)
    return redirect("listings:edit", revision_id=revision.pk)


@login_required
@require_POST
@private_view
def image_retry(request, revision_id, asset_id):
    revision = revision_for(request, revision_id)
    try:
        retry_image(actor=request.user, revision_id=revision.pk, asset_id=asset_id)
    except ObjectDoesNotExist:
        raise Http404() from None
    except ValidationError as error:
        return render(request, "listings/conflict.html", {"revision": revision, "error": error.messages[0]}, status=409)
    return redirect("listings:edit", revision_id=revision.pk)


@login_required
@require_GET
@private_view
def photo_status(request, revision_id):
    revision = revision_for(request, revision_id, reviewer=True)
    images = list(revision.images.all())
    return render(request, "listings/photos.html", {"revision": revision, "images": images,
                  "pending": any(link.asset.state == "pending" for link in images)})


@require_GET
@private_view
def public_image(request, listing_id, revision_id, asset_id):
    listing = get_object_or_404(public_listings(), pk=listing_id, public_revision_id=revision_id)
    link = get_object_or_404(RevisionImage.objects.select_related("asset"),
                            revision_id=revision_id, asset_id=asset_id,
                            asset__owner_id=listing.owner_id, asset__state="ready")
    if not link.asset.derivative.name:
        raise Http404()
    try:
        stream = link.asset.derivative.open("rb")
    except FileNotFoundError:
        raise Http404() from None
    return FileResponse(stream, content_type="image/jpeg", as_attachment=False, filename="ilan-fotografi.jpg")
