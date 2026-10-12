from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from allauth.mfa.models import Authenticator
from .models import SecurityEvent, User


@admin.register(User)
class AccountAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active")
    search_fields = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


# allauth registers raw JSON secret storage; this product never exposes it.
if admin.site.is_registered(Authenticator):
    admin.site.unregister(Authenticator)


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("actor_id", "action", "method", "created_at")
    readonly_fields = ("actor_id", "action", "method", "created_at")
    fields = readonly_fields
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
