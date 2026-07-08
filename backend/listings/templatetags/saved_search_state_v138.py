from django import template

register = template.Library()

DEFAULT_RENAME_ERROR_MESSAGE_V138 = "Type a new name before saving this saved search."


@register.simple_tag
def saved_search_rename_state_v138(request, search):
    """Centralized saved-search rename inline state for v138 template cleanup."""
    search_pk = getattr(search, "pk", None)

    renamed_id = getattr(request, "renamed_saved_search_id_v136", None)
    error_id = getattr(request, "saved_search_rename_error_id_v137", None)
    error_message = (
        getattr(request, "saved_search_rename_error_message_v137", None)
        or DEFAULT_RENAME_ERROR_MESSAGE_V138
    )

    has_error = error_id == search_pk
    was_renamed = renamed_id == search_pk

    helper_id = f"saved-search-rename-helper-{search_pk}-v135"
    error_id_attr = f"saved-search-rename-error-{search_pk}-v137"

    input_describedby = helper_id
    if has_error:
        input_describedby = f"{helper_id} {error_id_attr}"

    return {
        "has_error": has_error,
        "was_renamed": was_renamed,
        "error_message": error_message,
        "aria_expanded": "true" if has_error else "false",
        "aria_invalid": "true" if has_error else "false",
        "input_describedby": input_describedby,
    }
