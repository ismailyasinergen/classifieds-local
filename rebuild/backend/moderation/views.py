from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from listings.forms import add_service_errors
from listings.models import ListingRevision
from listings.publication import StalePublicRevision
from listings.services import InvalidRevisionState
from listings.views import attributes_for, private_view
from .forms import ReviewForm
from .policies import require_reviewer
from .services import approve_revision, reject_revision


@login_required
@require_GET
@private_view
def queue(request):
    require_reviewer(actor=request.user)
    queryset = ListingRevision.objects.filter(status="submitted").select_related(
        "listing", "category", "listing__public_revision").order_by("created_at", "pk")
    return render(request, "moderation/queue.html", {
        "page_obj": Paginator(queryset, 12).get_page(request.GET.get("page"))})


@login_required
@require_http_methods(["GET", "POST"])
@private_view
def review(request, revision_id):
    require_reviewer(actor=request.user)
    revision = get_object_or_404(ListingRevision.objects.select_related(
        "listing", "category", "attribute_schema", "listing__public_revision").prefetch_related("images__asset"), pk=revision_id)
    form = ReviewForm(request.POST if request.method == "POST" else None,
                      initial={"expected_public_revision_id": revision.listing.public_revision_id})
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            if form.cleaned_data["action"] == "approve":
                approve_revision(actor=request.user, revision_id=revision.pk,
                                 expected_public_revision_id=form.cleaned_data["expected_public_revision_id"],
                                 reason=form.cleaned_data["reason"])
            else:
                reject_revision(actor=request.user, revision_id=revision.pk, reason=form.cleaned_data["reason"])
        except (StalePublicRevision, InvalidRevisionState):
            form.add_error(None, "Bu inceleme ekranı güncelliğini yitirdi. Güncel sürümü açın.")
            status = 409
        except ValidationError as error:
            add_service_errors(form, error)
        else:
            messages.success(request, "İnceleme kararı kaydedildi.")
            return redirect("moderation:queue")
    return render(request, "moderation/review.html", {"revision": revision, "form": form,
                  "attributes": attributes_for(revision), "images": revision.images.all(),
                  "current": revision.listing.public_revision}, status=status)
