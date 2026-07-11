from __future__ import annotations

from django import template

from categories.navigation_v186 import build_category_navigation_context_v186


register = template.Library()


@register.simple_tag(takes_context=True)
def category_navigation_context_v186(context, selected_slug: str | None = None):
    request = context.get("request")
    query_params = getattr(request, "GET", None)
    path = getattr(request, "path", "")

    if not selected_slug and query_params is not None:
        selected_slug = query_params.get("category")

    return build_category_navigation_context_v186(
        selected_slug,
        query_params=query_params,
        path=path,
    )


@register.inclusion_tag("categories/_category_navigation_v186.html", takes_context=True)
def render_category_navigation_v186(context, selected_slug: str | None = None):
    request = context.get("request")
    query_params = getattr(request, "GET", None)
    path = getattr(request, "path", "")

    if not selected_slug and query_params is not None:
        selected_slug = query_params.get("category")

    return build_category_navigation_context_v186(
        selected_slug,
        query_params=query_params,
        path=path,
    )
