from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.utils import timezone

from listings.models import Listing
from listings.attribute_filters import apply_attribute_filters, get_attribute_filter_context, get_page_querystring

from .models import Category
from listings.listing_price_drop_sort_v279 import (
    apply_public_listing_sort_v279,
)


def apply_category_filters(queryset, request):
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
            | Q(category__name__icontains=q)
        )

    if location:
        queryset = queryset.filter(location__icontains=location)

    try:
        if min_price:
            queryset = queryset.filter(price__gte=Decimal(min_price))
    except InvalidOperation:
        pass

    try:
        if max_price:
            queryset = queryset.filter(price__lte=Decimal(max_price))
    except InvalidOperation:
        pass

    # RECENT_PRICE_DROP_SORT_V279
    queryset = apply_public_listing_sort_v279(
        queryset,
        request,
    )

    category_slug = getattr(getattr(request, "resolver_match", None), "kwargs", {}).get("slug", "")
    if not category_slug:
        category_slug = request.GET.get("category", "").strip()

    return apply_attribute_filters(queryset, request, category_slug)


class CategoryListingListView(ListView):
    model = Listing
    template_name = "listings/listing_list.html"
    context_object_name = "listings"
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        category_ids = self.category.get_descendant_ids()

        queryset = (
            Listing.objects
            .select_related("category", "owner")
            .prefetch_related("images")
            .filter(
                category_id__in=category_ids,
                status=Listing.Status.APPROVED,
            expires_at__gt=timezone.now(),
            )
        )

        return apply_category_filters(queryset, self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["root_categories"] = Category.objects.filter(parent__isnull=True).order_by("name")
        context["all_categories"] = Category.objects.all().order_by("name")
        context["current_category"] = self.category
        context["page_title"] = self.category.name
        context["search_q"] = self.request.GET.get("q", "")
        context["search_location"] = self.request.GET.get("location", "")
        context["search_min_price"] = self.request.GET.get("min_price", "")
        context["search_max_price"] = self.request.GET.get("max_price", "")
        context["search_category"] = ""
        context["search_sort"] = self.request.GET.get("sort", "newest")
        context.update(get_attribute_filter_context(self.request, self.category.slug))
        context["page_querystring"] = get_page_querystring(self.request)
        return context
