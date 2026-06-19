# PRIVATE_MEDIA_TEMPLATE_TAGS_V1
from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag
def private_file_url(obj, field_name, download=False):
    if not obj or not getattr(obj, "pk", None):
        return "#"

    meta = getattr(obj, "_meta", None)
    if not meta:
        return "#"

    try:
        url = reverse(
            "accounts:private_file_download",
            args=[
                meta.app_label,
                meta.model_name,
                obj.pk,
                field_name,
            ],
        )
    except NoReverseMatch:
        return "#"

    if download:
        return f"{url}?download=1"

    return url
