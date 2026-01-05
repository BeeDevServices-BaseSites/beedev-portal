# core/emails/portal_invites.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.timezone import localtime

def send_portal_invite_email(*, to_email: str, company_name: str, invite_url: str, invited_by_name: str = "", expires_at,) -> None:
    
    expires_local = localtime(expires_at)
    expires_str = expires_local.strftime("%B %d, %Y at %I:%M %p")

    ctx = {
        "company_name": company_name,
        "invite_url": invite_url,
        "invited_by_name": invited_by_name,
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", ""),
        "expires_at": expires_str
    }
    
    subject = f"Your BeeDev Portal Invite — {company_name}"
    text_body = render_to_string("emails/portal_invite.txt", ctx)
    html_body = render_to_string("emails/portal_invite.html", ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
