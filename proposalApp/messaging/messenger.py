# proposalApp/messenger.py
from typing import Iterable, Sequence
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

def send_proposal_email(proposal, emails: Sequence[str], signing_url: str, *, cc: Iterable[str] = (), attach_pdf: bool = False):
    if not emails:
        return

    subject = f"Proposal: {proposal.title} — {proposal.company.name}"
    context = {
        "proposal": proposal,
        "signing_url": signing_url,
        "company": proposal.company,
    }

    # Render templates (create these in step 3)
    body_txt = render_to_string("email/proposal_email.txt", context)
    body_html = render_to_string("email/proposal_email.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_txt,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=list(emails),
        cc=list(cc or ()),
    )
    msg.attach_alternative(body_html, "text/html")

    # Optional: attach generated/final PDF if you store it
    if attach_pdf and proposal.pdf:
        try:
            filename = proposal.pdf.name.rsplit("/", 1)[-1]
            msg.attach(filename, proposal.pdf.read(), "application/pdf")
        except Exception:
            pass

    msg.send(fail_silently=False)

    # Mark recipients as delivered
    now = timezone.now()
    for r in proposal.recipients.filter(email__in=emails):
        if not r.delivered_at:
            r.delivered_at = now
            r.save(update_fields=["delivered_at"])
