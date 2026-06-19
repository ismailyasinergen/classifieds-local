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
