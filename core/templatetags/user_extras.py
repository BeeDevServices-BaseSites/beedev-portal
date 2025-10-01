# userApp/templatetags/user_extras.py
from django import template

register = template.Library()

@register.filter
def user_name(u):
    if not u:
        return ""
    # display_name already falls back to username
    return getattr(u, "display_name", getattr(u, "username", ""))
