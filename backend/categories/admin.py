from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "slug"]
    list_filter = ["parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {
        "slug": ["name"],
    }

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered

from .models import Category


V182_CATEGORY_ADMIN_SAFEGUARDS_MARKER = "V182_CATEGORY_ADMIN_SAFEGUARDS"


try:
    admin.site.unregister(Category)
except NotRegistered:
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
