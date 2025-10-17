# proposalApp/public.py
from django.conf import settings
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.html import linebreaks
from django.views.decorators.http import require_http_methods
from ..models import Proposal
from core.utils.context import base_ctx
from django import forms
from django.urls import reverse, NoReverseMatch
from proposalApp.services.signature import save_signature_image_for_proposal, hash_current_document
from urllib.parse import urlencode, urljoin
from proposalApp.services.pdf_service import generate_proposal_pdf
from proposalApp.forms import SignProposalForm
from proposalApp.services.pdf_service import generate_proposal_pdf

def _public_base_url() -> str:
    base = getattr(settings, "PROPOSAL_PUBLIC_BASE_URL", None)
    if base:
        return base.rstrip("/")

    try:
        from django.contrib.sites.models import Site
        current = Site.objects.get_current()
        if getattr(current, "domain", None):
            scheme = getattr(settings, "DEFAULT_HTTP_SCHEME", "https")
            return f"{scheme}://{current.domain}".rstrip("/")
    except Exception:
        pass

    return "http://127.0.0.1:8000"

def _abs_url(url_or_path: str | None) -> str | None:
    if not url_or_path:
        return None
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return url_or_path
    base = _public_base_url()
    return urljoin(base + "/", url_or_path.lstrip("/"))

def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")

def _token_valid(p: Proposal) -> bool:
    return not (p.token_expires_at and timezone.now() > p.token_expires_at)

def _build_staff_pdf_context_from_proposal(p: Proposal):
    summary_md = getattr(getattr(p, "summary", None), "body_md", "") or ""
    summary_html = linebreaks(summary_md)

    notes_blocks = []
    for n in p.notes.filter(is_visible_to_client=True).order_by("sort_order", "pk"):
        notes_blocks.append({
            "subject": (n.subject or "").strip(),
            "body_html": linebreaks(n.body_md or ""),
        })

    hours_total = p.hours_total or getattr(p, "hours_subtotal", None) or Decimal("0.00")

    if p.converted_from_id and hasattr(p.converted_from, "valid_until_effective"):
        valid_until = p.converted_from.valid_until_effective
    else:
        valid_until = (p.created_at or timezone.now()).date() + timezone.timedelta(days=30)
    valid_days = max(1, (valid_until - (p.created_at or timezone.now()).date()).days)

    domain_text  = getattr(p, "maintenance_md", None) or "DNS Handling (included in 1st year) and Domain Renewals and record upkeep (optional for subsequent years or as needed)"
    hosting_text = getattr(p, "addons_md", None) or "$20 (monthly) or $200 (annually)"

    return {
        "company_name": p.company.name,
        "proposal_date": p.created_at,
        "quote_total": p.amount_total,
        "domain_text": domain_text,
        "hosting_text": hosting_text,
        "hours_total": hours_total,
        "summary_html": summary_html,
        "notes_blocks": notes_blocks,
        "deposit_amount": p.deposit_amount,
        "remaining_due": p.remaining_due,
        "valid_days": valid_days,
        "valid_until": valid_until,
    }

def _common_page_ctx(p: Proposal, title_text: str):
    return {
        "title": title_text,
        "heading": title_text,
        "page_heading": title_text,
        "title_short": p.title,
        "back_url": reverse("proposal_public:proposal_public_view", args=[p.sign_token]),
    }

def _account_signup_link(email: str | None) -> str | None:
    base = getattr(settings, "PROPOSAL_ACCOUNT_SIGNUP_URL", None)
    if not base:
        try:
            base = reverse("account_signup")
        except NoReverseMatch:
            base = None
    if not base:
        return None
    if email:
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}{urlencode({'email': email})}"
    return base

def _send_signed_confirmation(proposal, *, to_email: str | None):
    if not to_email:
        return

    subject = f"Fully Executed Proposal: {proposal.title} — {proposal.company.name}"
    # signup_url = _account_signup_link(getattr(proposal, "contact_email", None))
    # pdf_url = getattr(getattr(proposal, "pdf", None), "url", None)

    raw_signup = _account_signup_link(getattr(proposal, "contact_email", None))
    signup_url = _abs_url(raw_signup) if raw_signup else None

    raw_pdf = getattr(getattr(proposal, "pdf", None), "url", None)
    pdf_url = _abs_url(raw_pdf)

    lines = [
        f"Hi {proposal.contact_name or ''}".strip() or "Hello,",
        "",
        "Your proposal has been fully executed. Below are your links:",
    ]
    if pdf_url:
        lines.append(f"- Signed PDF: {pdf_url}")
    if signup_url:
        lines.append(f"- Create your account: {signup_url}")
    lines += [
        "",
        "If you have any questions, just reply to this email.",
        "",
        "— BeeDev Services",
    ]
    body_txt = "\n".join(lines)

    html_lines = [f"<p>{lines[0]}</p>", "<p>Your proposal has been fully executed.</p>", "<ul>"]
    if pdf_url:
        html_lines.append(f'<li>Signed PDF: <a href="{pdf_url}" target="_blank" rel="noopener">{pdf_url}</a></li>')
    if signup_url:
        html_lines.append(f'<li>Create your account: <a href="{signup_url}" target="_blank" rel="noopener">{signup_url}</a></li>')
    html_lines.append("</ul><p>If you have any questions, just reply to this email.</p><p>— BeeDev Services</p>")
    body_html = "".join(html_lines)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_txt,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
        cc=(getattr(settings, "PROPOSAL_CC", "") or "").split(",") if getattr(settings, "PROPOSAL_CC", "") else [],
        bcc=(getattr(settings, "PROPOSAL_BCC", "") or "").split(",") if getattr(settings, "PROPOSAL_BCC", "") else [],
        reply_to=[getattr(settings, "PROPOSAL_REPLY_TO", "")] if getattr(settings, "PROPOSAL_REPLY_TO", "") else None,
    )
    msg.attach_alternative(body_html, "text/html")
    try:
        msg.send(fail_silently=False)
    except Exception:
        pass

@require_http_methods(["GET"])
def public_proposal_view(request, token: str):
    p = get_object_or_404(Proposal, sign_token=token)
    if not _token_valid(p):
        return render(request, "proposals/token_expired.html", {"proposal": p}, status=403)

    p.mark_viewed(ip=_client_ip(request))

    title = p.title
    ctx = _build_staff_pdf_context_from_proposal(p)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    ctx.update({
        "proposal": p,
        "company": p.company,
    })
    return render(request, "proposals/public_view.html", ctx)

@require_http_methods(["GET", "POST"])
def public_proposal_sign(request, token: str):
    p = get_object_or_404(Proposal, sign_token=token)
    if not _token_valid(p):
        return render(request, "proposals/token_expired.html", {"proposal": p}, status=403)

    if p.signed_at:
        return render(request, "proposals/signed.html", {"proposal": p, **_common_page_ctx(p, f"Thank you!")})

    if request.method == "POST":
        form = SignProposalForm(request.POST, proposal=p)
        if form.is_valid():
            contact_email = (form.cleaned_data.get("contact_email") or "").strip()
            full_name = (form.cleaned_data.get("full_name") or "").strip()
            if contact_email and contact_email != (p.contact_email or "").strip():
                p.contact_email = contact_email
                p.save(update_fields=["contact_email"])
            if full_name and full_name != (p.contact_name or "").strip():
                p.contact_name = full_name
                p.save(update_fields=["contact_name"])

            payload = {
                "full_name": form.cleaned_data["full_name"],
                "accepted_terms": True,
                "agreed_e_records": form.cleaned_data.get("agree_e_records", False),
                "agreed_intent": form.cleaned_data.get("agree_intent", False),
                "signed_via": "public",
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "signed_at_iso": timezone.now().isoformat(),
            }

            p.mark_signed(
                actor=None,
                ip=_client_ip(request),
                signature_payload=payload,
                due_date=None,
                customer_user=None,
            )

            try:
                base_url = request.build_absolute_uri("/")
                generate_proposal_pdf(p, base_url=base_url, request=request, overwrite=True, delete_old=True)
            except Exception:
                pass

            _send_signed_confirmation(p, to_email=(p.contact_email or None))

            ctx = {"proposal": p, "full_name": payload["full_name"], **_common_page_ctx(p, "Thank you!")}
            return render(request, "proposals/signed.html", ctx)
    else:
        form = SignProposalForm()

    ctx = {"proposal": p, "form": form, **_common_page_ctx(p, f"{p.title} Proposal")}
    return render(request, "proposals/sign.html", ctx)