from django.contrib import admin

from .models import SellerStore, UserProfile


@admin.action(description="Approve seller verification")
def approve_verification(modeladmin, request, queryset):
    queryset.update(verification_status=UserProfile.VerificationStatus.APPROVED)


@admin.action(description="Reject seller verification")
def reject_verification(modeladmin, request, queryset):
    queryset.update(verification_status=UserProfile.VerificationStatus.REJECTED)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "phone",
        "location",
        "business_name",
        "verification_status",
    ]
    list_filter = [
        "verification_status",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "business_name",
        "phone",
        "location",
    ]
    actions = [
        approve_verification,
        reject_verification,
    ]



@admin.register(SellerStore)
class SellerStoreAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "owner",
        "slug",
        "location",
        "has_logo",
        "has_banner",
        "is_active",
        "updated_at",
    ]
    list_filter = [
        "is_active",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "name",
        "headline",
        "description",
        "location",
        "owner__username",
        "owner__email",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]


    @admin.display(boolean=True, description="Logo")
    def has_logo(self, obj):
        return bool(obj.logo)

    @admin.display(boolean=True, description="Banner")
    def has_banner(self, obj):
        return bool(obj.banner)


# TRUST_SAFETY_EVENT_ADMIN_V1
from django.contrib import admin as _trust_safety_admin

try:
    from .models import TrustSafetyEvent

    @_trust_safety_admin.register(TrustSafetyEvent)
    class TrustSafetyEventAdmin(_trust_safety_admin.ModelAdmin):
        list_display = (
            "id",
            "event_type",
            "actor",
            "target_user",
            "listing",
            "created_at",
        )
        list_filter = ("event_type", "created_at")
        search_fields = (
            "title",
            "public_note",
            "internal_note",
            "actor__username",
            "actor__email",
            "target_user__username",
            "target_user__email",
            "listing__title",
        )
        readonly_fields = ("created_at",)
except _trust_safety_admin.sites.AlreadyRegistered:
    pass

# V209_SELLER_STORE_ADMIN_UI_POLISH START
V209_SELLER_STORE_ADMIN_UI_POLISH = "V209_SELLER_STORE_ADMIN_UI_POLISH"

from django.db import models as _v209_models
from django.db.models import Q as _v209_Q
from django.contrib import admin as _v209_admin

from .models import SellerStore as _V209SellerStore


def _v209_model_field_names(model):
    return {field.name for field in model._meta.fields}


def _v209_model_field(model, field_name):
    try:
        return model._meta.get_field(field_name)
    except Exception:
        return None


def _v209_first_existing_field(model, candidates):
    field_names = _v209_model_field_names(model)
    for candidate in candidates:
        if candidate in field_names:
            return candidate
    return None


def _v209_safe_value(obj, candidates):
    for candidate in candidates:
        try:
            value = getattr(obj, candidate)
        except Exception:
            continue

        if callable(value):
            continue

        if value not in (None, ""):
            return value

    return None


def _v209_boolean_status(obj):
    for candidate in ("is_verified", "verified", "is_active", "active", "published"):
        value = _v209_safe_value(obj, (candidate,))
        if value is True:
            return "Verified"
        if value is False:
            return "Needs review"

    return "Review"


def _v209_text_profile_status(obj):
    for candidate in ("description", "store_description", "about", "bio", "tagline"):
        value = _v209_safe_value(obj, (candidate,))
        if isinstance(value, str) and value.strip():
            return "Profile copy added"

    return "Needs profile copy"


class _V209SellerStoreProfileCompletenessFilter(_v209_admin.SimpleListFilter):
    title = "Profile polish"
    parameter_name = "v209_profile"

    def lookups(self, request, model_admin):
        return (
            ("with_description", "Profile copy added"),
            ("missing_description", "Needs profile copy"),
            ("verified", "Verified / active"),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if not value:
            return queryset

        description_field = _v209_first_existing_field(
            queryset.model,
            ("description", "store_description", "about", "bio", "tagline"),
        )

        if value == "with_description" and description_field:
            return queryset.exclude(**{f"{description_field}__isnull": True}).exclude(
                **{description_field: ""}
            )

        if value == "missing_description" and description_field:
            return queryset.filter(
                _v209_Q(**{f"{description_field}__isnull": True})
                | _v209_Q(**{description_field: ""})
            )

        if value == "verified":
            boolean_field = _v209_first_existing_field(
                queryset.model,
                ("is_verified", "verified", "is_active", "active", "published"),
            )
            if boolean_field:
                return queryset.filter(**{boolean_field: True})

        return queryset


try:
    _v209_admin.site.unregister(_V209SellerStore)
except _v209_admin.sites.NotRegistered:
    pass


@_v209_admin.register(_V209SellerStore)
class SellerStoreAdmin(_v209_admin.ModelAdmin):
    v209_seller_store_admin_ui_polish = True

    list_display = (
        "v209_store_identity",
        "v209_owner_label",
        "v209_profile_status",
        "v209_updated_label",
    )
    search_fields = ("=id",)
    list_filter = (_V209SellerStoreProfileCompletenessFilter,)
    readonly_fields = (
        "v209_profile_summary",
        "v209_created_label",
        "v209_updated_label",
    )
    ordering = ("-id",)
    list_per_page = 50

    def get_search_fields(self, request):
        search_fields = ["=id"]

        for candidate in ("name", "store_name", "title", "slug", "business_name"):
            field = _v209_model_field(self.model, candidate)
            if isinstance(
                field,
                (
                    _v209_models.CharField,
                    _v209_models.TextField,
                    _v209_models.SlugField,
                ),
            ):
                search_fields.append(candidate)

        for relation in ("user", "owner", "seller"):
            field = _v209_model_field(self.model, relation)
            remote_model = getattr(getattr(field, "remote_field", None), "model", None)
            if remote_model is None:
                continue

            remote_field_names = _v209_model_field_names(remote_model)
            if "username" in remote_field_names:
                search_fields.append(f"{relation}__username")
            if "email" in remote_field_names:
                search_fields.append(f"{relation}__email")

        return tuple(dict.fromkeys(search_fields))

    def get_list_select_related(self, request):
        related_fields = []

        for relation in ("user", "owner", "seller"):
            field = _v209_model_field(self.model, relation)
            if getattr(field, "remote_field", None) is not None:
                related_fields.append(relation)

        return tuple(related_fields)

    @_v209_admin.display(description="Store")
    def v209_store_identity(self, obj):
        value = _v209_safe_value(
            obj,
            ("name", "store_name", "title", "business_name", "slug"),
        )
        if value:
            return value

        primary_key = getattr(obj, "pk", None)
        return f"Seller store #{primary_key or 'new'}"

    @_v209_admin.display(description="Owner")
    def v209_owner_label(self, obj):
        owner = _v209_safe_value(obj, ("user", "owner", "seller"))
        if owner:
            return owner

        return "Unassigned"

    @_v209_admin.display(description="Profile status")
    def v209_profile_status(self, obj):
        boolean_status = _v209_boolean_status(obj)
        if boolean_status == "Verified":
            return "Verified"

        return _v209_text_profile_status(obj)

    @_v209_admin.display(description="Updated")
    def v209_updated_label(self, obj):
        value = _v209_safe_value(
            obj,
            ("updated_at", "modified_at", "created_at", "created"),
        )
        if value:
            return value

        return "Not recorded"

    @_v209_admin.display(description="Created")
    def v209_created_label(self, obj):
        value = _v209_safe_value(obj, ("created_at", "created", "date_joined"))
        if value:
            return value

        return "Not recorded"

    @_v209_admin.display(description="Profile summary")
    def v209_profile_summary(self, obj):
        identity = self.v209_store_identity(obj)
        owner = self.v209_owner_label(obj)
        status = self.v209_profile_status(obj)
        return f"{identity} · {owner} · {status}"
# V209_SELLER_STORE_ADMIN_UI_POLISH END

# V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS START
V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS = (
    "V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS"
)

V215_SELLER_STORE_REVIEW_EXPORT_ACTION_NAME = (
    "v215_export_selected_seller_stores_for_review"
)
V215_SELLER_STORE_REVIEW_EXPORT_MAX_ROWS = 250


def _v215_seller_store_csv_safe(value):
    text = "" if value is None else str(value)
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def _v215_seller_store_attr(instance, names, default=""):
    for name in names:
        if hasattr(instance, name):
            value = getattr(instance, name)
            if callable(value):
                continue
            if value is not None:
                return value
    return default


def _v215_seller_store_owner_label(instance):
    for name in ("user", "owner", "seller"):
        related = getattr(instance, name, None)
        if related is None:
            continue

        get_username = getattr(related, "get_username", None)
        if callable(get_username):
            username = get_username()
            if username:
                return username

        email = getattr(related, "email", "")
        if email:
            return email

        return related

    return ""


def _v215_seller_store_message_user(modeladmin, request, message, *, level_name="info"):
    if request is None:
        return

    try:
        from django.contrib import messages

        level = {
            "error": messages.ERROR,
            "warning": messages.WARNING,
            "success": messages.SUCCESS,
            "info": messages.INFO,
        }.get(level_name, messages.INFO)

        modeladmin.message_user(request, message, level=level)
    except Exception:
        return


def v215_export_selected_seller_stores_for_review(modeladmin, request, queryset):
    """Export selected SellerStore rows for manual review without mutating them."""

    if request is not None and not modeladmin.has_view_permission(request):
        _v215_seller_store_message_user(
            modeladmin,
            request,
            "You do not have permission to export seller-store review rows.",
            level_name="error",
        )
        return None

    selected_count = queryset.count()

    if selected_count <= 0:
        _v215_seller_store_message_user(
            modeladmin,
            request,
            "Select at least one seller store to export for review.",
            level_name="warning",
        )
        return None

    if selected_count > V215_SELLER_STORE_REVIEW_EXPORT_MAX_ROWS:
        _v215_seller_store_message_user(
            modeladmin,
            request,
            (
                "Seller-store review export is limited to "
                f"{V215_SELLER_STORE_REVIEW_EXPORT_MAX_ROWS} rows at a time."
            ),
            level_name="error",
        )
        return None

    import csv

    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="seller-store-review-export-v215.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "id",
            "store",
            "owner",
            "profile_status",
            "verified",
            "approved",
            "created_at",
            "updated_at",
        ]
    )

    for seller_store in queryset.order_by("pk"):
        writer.writerow(
            [
                _v215_seller_store_csv_safe(seller_store.pk),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_attr(
                        seller_store,
                        ("store_name", "name", "title", "business_name"),
                    )
                ),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_owner_label(seller_store)
                ),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_attr(
                        seller_store,
                        ("profile_status", "status", "state"),
                    )
                ),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_attr(
                        seller_store,
                        ("is_verified", "verified"),
                    )
                ),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_attr(
                        seller_store,
                        ("is_approved", "approved"),
                    )
                ),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_attr(
                        seller_store,
                        ("created_at", "created"),
                    )
                ),
                _v215_seller_store_csv_safe(
                    _v215_seller_store_attr(
                        seller_store,
                        ("updated_at", "updated", "modified_at"),
                    )
                ),
            ]
        )

    _v215_seller_store_message_user(
        modeladmin,
        request,
        f"Exported {selected_count} seller-store review row(s).",
        level_name="success",
    )

    return response


v215_export_selected_seller_stores_for_review.short_description = (
    "Export selected seller stores for review"
)


def _v215_install_seller_store_admin_actions():
    registered_admin = admin.site._registry.get(SellerStore)
    if registered_admin is None:
        return False

    admin_class = registered_admin.__class__

    if getattr(admin_class, "v215_seller_store_admin_action_installed", False):
        return True

    original_get_actions = admin_class.get_actions

    def _v215_seller_store_get_actions(self, request):
        action_map = dict(original_get_actions(self, request))
        action_map.pop("delete_selected", None)

        if request is not None and self.has_view_permission(request):
            action_map[V215_SELLER_STORE_REVIEW_EXPORT_ACTION_NAME] = (
                v215_export_selected_seller_stores_for_review,
                V215_SELLER_STORE_REVIEW_EXPORT_ACTION_NAME,
                v215_export_selected_seller_stores_for_review.short_description,
            )

        return action_map

    admin_class.get_actions = _v215_seller_store_get_actions
    admin_class.v215_seller_store_admin_action_installed = True
    admin_class.v215_seller_store_admin_action_name = (
        V215_SELLER_STORE_REVIEW_EXPORT_ACTION_NAME
    )

    return True


_v215_install_seller_store_admin_actions()
# V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS END
