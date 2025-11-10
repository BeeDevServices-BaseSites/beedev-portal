from django import template

register = template.Library()

@register.filter
def user_name(u):
    if not u:
        return ""
    return getattr(u, "display_name", getattr(u, "username", ""))
