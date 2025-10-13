# proposalApp/messenger.py
from __future__ import annotations
from typing import Iterable, Sequence
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

def _parse_list(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, (list, tuple, set)):
        items = list(val)
    else:
        items = str(val).replace(";", ",").split(",")
    out, seen = [], set()
    for s in items:
        e = (s or "").strip()
        k = e.lower()
        if e and k not in seen:
            seen.add(k); out.append(e)
    return out

def send_proposal_email(
    proposal,
    emails: Sequence[str],
    signing_url: str,
    *,
    cc: Iterable[str] = (),
    attach_pdf: bool | None = None,   # ignored on purpose (no attachment)
    **kwargs,
):
    to_list  = _parse_list(emails)
    if not to_list:
        return

    # CC/BCC from env + optional per-call cc
    cc_final  = _parse_list(cc) + _parse_list(getattr(settings, "PROPOSAL_CC", ""))
    bcc_final = _parse_list(getattr(settings, "PROPOSAL_BCC", ""))

    # Force a domain Reply-To so Gmail doesn’t inject the gmail.com one
    reply_to = _parse_list(getattr(settings, "PROPOSAL_REPLY_TO", "")) or [to_list[0]]

    subject = f"Proposal: {proposal.title} — {proposal.company.name}"
    ctx = {"proposal": proposal, "signing_url": signing_url, "company": proposal.company}
    body_txt = render_to_string("email/proposal_email.txt", ctx)
    body_html = render_to_string("email/proposal_email.html", ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_txt or strip_tags(body_html),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),  # e.g. "BeeDev Services <proposals@beedev-services.com>"
        to=to_list,
        cc=cc_final or None,
        bcc=bcc_final or None,
        reply_to=reply_to or None,
        headers={"X-Entity": "proposal", "X-Proposal-ID": str(proposal.pk)},
    )
    if body_html:
        msg.attach_alternative(body_html, "text/html")

    msg.send(fail_silently=False)

    # Mark only primary recipients as delivered
    now = timezone.now()
    for r in proposal.recipients.filter(email__in=to_list):
        if not r.delivered_at:
            r.delivered_at = now
            r.save(update_fields=["delivered_at"])
