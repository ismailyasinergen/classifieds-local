from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import render
from accounts.mfa_middleware import remediation
from accounts.mfa_policy import verified_current_email
from accounts.rate_limits import ActionRateLimited
from listings.forms import add_service_errors
from .case_inputs import CaseConflict
from .case_policies import require_case_actor


def case_view(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not verified_current_email(request.user):
            return remediation(request, "accounts:verify_email")
        require_case_actor(actor=request.user)
        try:
            return view(request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise Http404() from None
        except CaseConflict as error:
            return HttpResponse(error.messages[0], status=409, content_type="text/plain; charset=utf-8")
    return wrapped


def form_page(request, template, form, context, submit):
    status, retry = 200, None
    if request.method == "POST" and form.is_valid():
        try:
            return submit(form.cleaned_data)
        except ValidationError as error:
            add_service_errors(form, error)
            if isinstance(error, CaseConflict):
                status = 409
            elif isinstance(error, ActionRateLimited):
                status, retry = 429, error.retry_after
    response = render(request, "moderation/cases/" + template + ".html", context | {"form": form}, status=status)
    if retry is not None:
        response["Retry-After"] = str(retry)
    return response


def history_page(request, template, queryset, projection):
    page = Paginator(queryset, 12).get_page(request.GET.get("page"))
    def link(number):
        params = request.GET.copy()
        params["page"] = number
        return "?" + params.urlencode()
    return render(request, "moderation/cases/" + template + ".html", {
        "page_number": page.number, "page_count": page.paginator.num_pages,
        "items": [projection(row) for row in page],
        "previous_url": link(page.previous_page_number()) if page.has_previous() else None,
        "next_url": link(page.next_page_number()) if page.has_next() else None,
    })
