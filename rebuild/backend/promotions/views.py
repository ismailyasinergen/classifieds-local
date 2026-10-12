from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from listings.models import Listing
from listings.queries import public_listings
from .forms import PurchaseForm
from .models import Activation, Purchase
from .services import complete_demo, purchase_demo, require_actor, require_demo


@login_required
@require_http_methods(["GET", "POST"])
def choose(request, listing_id):
    require_demo()
    listing = get_object_or_404(Listing, pk=listing_id, owner=request.user)
    require_actor(request.user, listing, request)
    form = PurchaseForm(request.POST if request.method == "POST" else None, actor=request.user)
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            purchase = purchase_demo(actor=request.user, listing_id=listing.pk,
                product_id=form.cleaned_data["product"].pk, key=form.cleaned_data["key"], request=request)
        except ObjectDoesNotExist:
            raise Http404() from None
        except ValidationError as error:
            form.add_error(None, error)
            status = 409
        else:
            return redirect("promotions:status", purchase_id=purchase.pk)
    elif request.method == "POST":
        status = 400
    return render(request, "promotions/choose.html", {"listing":listing,"form":form,
        "eligible":public_listings().filter(pk=listing.pk).exists()}, status=status)


@login_required
@require_GET
def status(request, purchase_id):
    require_demo()
    purchase = get_object_or_404(Purchase.objects.select_related("listing"), pk=purchase_id, owner=request.user)
    require_actor(request.user, purchase.listing, request)
    activation = Activation.objects.filter(purchase=purchase).first()
    now = timezone.now()
    visible = public_listings(at=now).filter(pk=purchase.listing_id).exists()
    return render(request, "promotions/status.html", {"purchase":purchase,"activation":activation,
        "active":bool(activation and activation.starts_at <= now < activation.ends_at),"visible":visible})


@login_required
@require_POST
def complete(request, purchase_id):
    require_demo()
    get_object_or_404(Purchase, pk=purchase_id, owner=request.user)
    try:
        complete_demo(actor=request.user, purchase_id=purchase_id, request=request)
    except ObjectDoesNotExist:
        raise Http404() from None
    except ValidationError as error:
        return render(request, "promotions/conflict.html", {"error":error.messages[0]}, status=409)
    return redirect("promotions:status", purchase_id=purchase_id)