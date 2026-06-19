from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import ModerationAppeal


@login_required
def my_moderation_appeals(request):
    queryset = ModerationAppeal.objects.filter(appellant=request.user)

    field_names = {field.name for field in ModerationAppeal._meta.fields}
    if "created_at" in field_names:
        queryset = queryset.order_by("-created_at", "-id")
    else:
        queryset = queryset.order_by("-id")

    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/my_moderation_appeals.html",
        {
            "appeals": page_obj.object_list,
            "page_obj": page_obj,
        },
    )
