from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def dev_demo_login_enabled():
    return bool(settings.DEBUG)
