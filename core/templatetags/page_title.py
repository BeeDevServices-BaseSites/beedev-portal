from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter
def stylize_title(value, css_class="altTitle"):
    if not value:
        return ""
    s = str(value).strip()
    if not s:
        return ""

    parts = s.split()
    if len(parts) >= 2:
        head = " ".join(parts[:-1])
        tail = parts[-1]
        return format_html('{} <span class="{}">{}</span>', head, css_class, tail)

    n = len(s)
    cut = (n // 2)
    left, right = s[:cut], s[cut:]
    return format_html('{}<span class="{}">{}</span>', left, css_class, right)
