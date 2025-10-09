from decimal import Decimal
from django.contrib.auth import get_user_model
from typing import Iterable, Sequence
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

def create_account_for_signed_proposal(proposal):
    rcpt = proposal.recipients.filter(is_primary=True).first() or proposal.recipients.first()
    if not rcpt:
        return None
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=rcpt.email,
        defaults={"username": rcpt.email.split("@")[0], "first_name": rcpt.name or ""}
    )
    return user

def create_invoice_for_deposit(proposal, amount: Decimal, kind: str):
    try:
        from invoiceApp.models import Invoice
        inv = Invoice.objects.create(
            company=proposal.company,
            title=f"Deposit for {proposal.title}",
            amount=amount,
            kind=kind,
            proposal_ref=str(proposal.pk),
        )
        return inv
    except Exception:
        class Stub:
            id = f"INV-{proposal.pk}-{int(amount)}"
        return Stub()

def send_proposal_email(proposal, recipients: Sequence[str], signing_url: str, **kwargs):
    if not recipients:
        return

    cc = list(kwargs.get("cc") or [])
    attach_pdf = bool(kwargs.get("attach_pdf", False))

    subject = f"Proposal: {proposal.title} — {proposal.company.name}"
    context = {
        "proposal": proposal,
        "company": proposal.company,
        "signing_url": signing_url,
    }

    # Render both text & html
    body_txt = render_to_string("proposals/email.txt", context)
    body_html = render_to_string("proposals/email.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_txt,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=list(recipients),
        cc=cc,
        reply_to=[proposal.created_by.email] if getattr(proposal.created_by, "email", None) else None,
    )
    msg.attach_alternative(body_html, "text/html")

    # Optional: attach finalized PDF if present & requested
    # if attach_pdf and proposal.pdf:
    #     try:
    #         filename = proposal.pdf.name.rsplit("/", 1)[-1]
    #         msg.attach(filename, proposal.pdf.read(), "application/pdf")
    #     except Exception:
    #         pass

    msg.send(fail_silently=False)

    # Stamp delivered_at on matching ProposalRecipient rows
    now = timezone.now()
    proposal.recipients.filter(email__in=recipients, delivered_at__isnull=True)\
        .update(delivered_at=now)
