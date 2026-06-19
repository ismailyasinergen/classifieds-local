# NAV_EXTRAS_SAFE_URL_V1
from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag
def safe_url(view_name, *args, **kwargs):
    try:
        return reverse(view_name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "#"


@register.filter
def nonzero(value):
    try:
        return int(value) > 0
    except Exception:
        return False
