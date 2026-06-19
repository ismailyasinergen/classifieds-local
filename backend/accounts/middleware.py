from django.contrib import messages
from django.shortcuts import redirect

from .models import UserProfile


class SellerRestrictionMiddleware:
    """
    Server-side protection for suspended sellers.
    Staff/admin users are never blocked.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated or user.is_staff:
            return None

        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            return None

        path = (request.path or "").lower()
        match = getattr(request, "resolver_match", None)
        namespace = (getattr(match, "namespace", "") or "").lower()
        url_name = (getattr(match, "url_name", "") or "").lower()

        if profile.is_seller_suspended:
            seller_action_names = {
                "listing_create",
                "listing_add",
                "listing_update",
                "listing_edit",
                "listing_delete",
                "listing_archive",
                "listing_renew",
                "listing_promote",
                "promotion_request",
                "promotion_checkout",
                "promotion_create",
                "promotion_cancel",
                "request_promotion",
            }

            seller_action_path = (
                path.startswith("/listings/")
                and any(
                    token in path
                    for token in [
                        "/create",
                        "/new",
                        "/add",
                        "/edit",
                        "/update",
                        "/delete",
                        "/archive",
                        "/renew",
                        "/promote",
                    ]
                )
            )

            promotion_action_path = path.startswith("/promotions/")

            if (
                url_name in seller_action_names
                or seller_action_path
                or promotion_action_path
            ):
                messages.error(
                    request,
                    "Your seller account is temporarily suspended. You cannot create, edit, archive, delete, renew, or promote listings during this restriction.",
                )
                return redirect("accounts:dashboard")

        if profile.is_seller_messaging_blocked:
            messaging_action_names = {
                "contact_seller",
                "thread_reply",
                "reply",
                "send",
                "compose",
            }

            messaging_action_path = (
                path.startswith("/conversations/")
                and any(
                    token in path
                    for token in [
                        "/contact",
                        "/reply",
                        "/send",
                        "/compose",
                    ]
                )
            )

            if namespace == "conversations" and (
                url_name in messaging_action_names or messaging_action_path
            ):
                messages.error(
                    request,
                    "Your messaging access is temporarily blocked by moderation.",
                )
                return redirect("conversations:inbox")

        return None



# SENSITIVE_MEDIA_BLOCK_MIDDLEWARE_V1
class SensitiveMediaBlockMiddleware:
    """
    Blocks direct /media/ access to sensitive uploads.

    Sensitive files must be served through authenticated protected views.
    Listing images and other public media are not blocked unless their path
    contains one of the sensitive folder names below.
    """

    SENSITIVE_PATH_PARTS = {
        "appeal_attachments",
        "verification_documents",
        "verification_docs",
        "seller_verification",
        "payment_proofs",
        "promotion_proofs",
        "payment_receipts",
        "receipts",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.http import HttpResponseNotFound

        media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"
        path = request.path.lower()

        if path.startswith(media_url.lower()):
            normalized = path.replace("\\", "/")
            if any(part in normalized for part in self.SENSITIVE_PATH_PARTS):
                return HttpResponseNotFound("File not found.")

        return self.get_response(request)



# CUSTOM_405_ERROR_PAGE_MIDDLEWARE_V1
class CustomMethodNotAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code == 405:
            try:
                from django.shortcuts import render

                return render(
                    request,
                    "405.html",
                    {
                        "page_title": "Method not allowed",
                    },
                    status=405,
                )
            except Exception:
                return response

        return response
