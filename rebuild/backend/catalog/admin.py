from django.contrib import admin
from .models import AttributeSchema, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")
    list_select_related = ("parent",)
    search_fields = ("name", "slug")


@admin.register(AttributeSchema)
class AttributeSchemaAdmin(admin.ModelAdmin):
    list_display = ("category", "version", "created_at")
    list_select_related = ("category",)
    readonly_fields = ("category", "version", "definition", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
