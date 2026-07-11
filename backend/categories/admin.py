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
# V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH
def _v196_category_parent_path(self, obj):
    """Return a compact parent chain without changing the admin list_display contract."""
    parent = getattr(obj, "parent", None)
    labels = []
    guard = 0

    while parent is not None and guard < 12:
        labels.append(str(parent))
        parent = getattr(parent, "parent", None)
        guard += 1

    if not labels:
        return "Top-level"

    return " › ".join(reversed(labels))


_v196_category_parent_path.short_description = "Parent path"
_v196_category_parent_path.admin_order_field = "parent__name"


def _v196_category_child_count(self, obj):
    """Return direct child count without assuming a specific related manager name."""
    children = getattr(obj, "children", None)

    if children is not None and hasattr(children, "count"):
        return children.count()

    fallback_children = getattr(obj, "category_set", None)

    if fallback_children is not None and hasattr(fallback_children, "count"):
        return fallback_children.count()

    return 0


_v196_category_child_count.short_description = "Children"


def _v196_category_status_label(self, obj):
    """Return a readable active/inactive label without changing existing admin fields."""
    if hasattr(obj, "is_active"):
        return "Active" if obj.is_active else "Inactive"

    return "Available"


_v196_category_status_label.short_description = "Status"
_v196_category_status_label.admin_order_field = "is_active"


def _v196_append_unique_tuple(existing, values):
    if existing is True:
        return True

    if existing in (None, False):
        normalized = []
    elif isinstance(existing, str):
        normalized = [existing]
    else:
        normalized = list(existing)

    for item in values:
        if item and item not in normalized:
            normalized.append(item)

    return tuple(normalized)


def _v196_category_field_names(model):
    return {field.name for field in model._meta.get_fields() if hasattr(field, "name")}


def _v196_apply_category_admin_ux_polish():
    from django.contrib import admin as _django_admin
    from .models import Category as _V196Category

    category_admin = _django_admin.site._registry.get(_V196Category)

    if category_admin is None:
        return

    admin_class = category_admin.__class__
    field_names = _v196_category_field_names(_V196Category)

    # Preserve the v182/v185 admin field contract. Do not mutate list_display,
    # list_filter, search_fields, or readonly_fields here.
    admin_class.v196_preserved_list_display_contract = tuple(
        getattr(admin_class, "list_display", ())
    )
    admin_class.v196_preserved_list_filter_contract = tuple(
        getattr(admin_class, "list_filter", ())
    )
    admin_class.v196_preserved_search_fields_contract = tuple(
        getattr(admin_class, "search_fields", ())
    )

    setattr(admin_class, "v196_parent_path", _v196_category_parent_path)
    setattr(admin_class, "v196_child_count", _v196_category_child_count)
    setattr(admin_class, "v196_status_label", _v196_category_status_label)

    if "parent" in field_names:
        admin_class.list_select_related = _v196_append_unique_tuple(
            getattr(admin_class, "list_select_related", ()),
            ["parent"],
        )

    admin_class.list_per_page = 50
    admin_class.save_on_top = True
    admin_class.actions_on_top = True
    admin_class.show_full_result_count = False
    admin_class.preserve_filters = True

    admin_class.v196_category_taxonomy_admin_ux_polish = True


_v196_apply_category_admin_ux_polish()
