from decimal import Decimal
from django.contrib.auth import get_user_model
from typing import Iterable, Sequence
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

def _extract_sender_name_and_title(sender_user):
    """
    Returns (name, title) using existing fields only.
    - name: full_name -> first/last -> username/email
    - title: user.profile.job_title (or similar) -> role display -> groups
    - defaults: title -> 'Engineering Team'
    """
    if not sender_user:
        return None, "Engineering Team"

    # --- name ---
    name = ""
    try:
        name = (sender_user.get_full_name() or "").strip()
    except Exception:
        pass
    if not name:
        first = (getattr(sender_user, "first_name", "") or "").strip()
        last  = (getattr(sender_user, "last_name", "") or "").strip()
        name = (f"{first} {last}").strip()
    if not name:
        name = getattr(sender_user, "username", "") or getattr(sender_user, "email", "")

    # --- job title (prefer profile.job_title) ---
    def _find_job_title(u):
        # Try common locations in your project
        for path in ("profile.job_title", "employee_profile.job_title", "job_title"):
            node = u
            try:
                for part in path.split("."):
                    node = getattr(node, part, None)
                    if node is None:
                        break
                if node:
                    return str(node).strip()
            except Exception:
                pass

        try:
            if hasattr(u, "get_role_display"):
                disp = u.get_role_display()
                if disp:
                    return str(disp).strip()
        except Exception:
            pass

        try:
            gnames = set(u.groups.values_list("name", flat=True))
            if u.is_superuser or "Owner" in gnames:
                return "Owner"
            if "Admin" in gnames:
                return "Admin"
            if "HR" in gnames:
                return "HR"
            if u.is_staff:
                return "Employee"
        except Exception:
            pass

        return None

    title = _find_job_title(sender_user) or "Engineering Team"
    return name, title

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

    sender_user = kwargs.get("sender_user")
    sender_name, sender_title = _extract_sender_name_and_title(sender_user)
    cc = list(kwargs.get("cc") or [])
    attach_pdf = bool(kwargs.get("attach_pdf", False))

    subject = f"Proposal: {proposal.title} — {proposal.company.name}"
    context = {
        "proposal": proposal,
        "company": proposal.company,
        "signing_url": signing_url,
        "sender_name": sender_name,
        "sender_title": sender_title,
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
