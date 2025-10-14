# proposalApp/public.py
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.html import linebreaks
from django.views.decorators.http import require_http_methods
from ..models import Proposal
from core.utils.context import base_ctx
from django import forms
from django.urls import reverse
from proposalApp.services.signature import save_signature_image_for_proposal, hash_current_document

def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")

def _token_valid(p: Proposal) -> bool:
    return not (p.token_expires_at and timezone.now() > p.token_expires_at)

def _build_staff_pdf_context_from_proposal(p: Proposal):
    """
    Produce the same variables your staff PDF template expects, using only
    fields that exist on Proposal (and its related objects).
    """
    # Summary → HTML (simple paragraphs; your staff view passed summary_html already)
    summary_md = getattr(getattr(p, "summary", None), "body_md", "") or ""
    summary_html = linebreaks(summary_md)

    # Visible notes → [{subject, body_html}]
    notes_blocks = []
    for n in p.notes.filter(is_visible_to_client=True).order_by("sort_order", "pk"):
        notes_blocks.append({
            "subject": (n.subject or "").strip(),
            "body_html": linebreaks(n.body_md or ""),
        })

    # Hours
    hours_total = p.hours_total or getattr(p, "hours_subtotal", None) or Decimal("0.00")

    # Valid-until: copy from Draft if present; else default 30 days from created_at
    if p.converted_from_id and hasattr(p.converted_from, "valid_until_effective"):
        valid_until = p.converted_from.valid_until_effective
    else:
        valid_until = (p.created_at or timezone.now()).date() + timezone.timedelta(days=30)
    valid_days = max(1, (valid_until - (p.created_at or timezone.now()).date()).days)

    # Domain/hosting text: use optional narrative fields if they exist on Proposal,
    # otherwise provide safe fallbacks. (These are just short strings in your PDF.)
    domain_text  = getattr(p, "maintenance_md", None) or "DNS Handling (included in 1st year) and Domain Renewals and record upkeep (optional for subsequent years or as needed)"
    hosting_text = getattr(p, "addons_md", None)      or "$20 (monthly) or $200 (annually)"

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
    """Shared page heading + back link."""
    return {
        "title": title_text,
        "heading": title_text,
        "page_heading": title_text,
        "title_short": p.title,
        "back_url": reverse("proposal_public:proposal_public_view", args=[p.sign_token]),
    }

class SignProposalForm(forms.Form):
    full_name = forms.CharField(max_length=160, label="Your full name")
    accept    = forms.BooleanField(label="I agree to the proposal and terms")

@require_http_methods(["GET"])
def public_proposal_view(request, token: str):
    p = get_object_or_404(Proposal, sign_token=token)
    if not _token_valid(p):
        return render(request, "proposals/token_expired.html", {"proposal": p}, status=403)

    # Record first view
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

    # If already signed, just show the confirmation page
    if p.signed_at:
        return render(request, "proposals/signed.html", {"proposal": p, **_common_page_ctx(p, f"Thank you!")})

    if request.method == "POST":
        form = SignProposalForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data["full_name"].strip()
            sig_path = save_signature_image_for_proposal(p, full_name)
            payload = {
                "role": "CLIENT",
                "full_name": full_name,
                "email": p.contact_email,  # or form.cleaned_data.get("email") if you collect it
                "signature_image": sig_path,
                "ip": _client_ip(request),
                "ua": request.META.get("HTTP_USER_AGENT", ""),
                "consents": {
                    "e_record_consent": bool(form.cleaned_data["agree_e_records"]),
                    "intent_confirmed": bool(form.cleaned_data["agree_intent"]),
                    "terms_version": timezone.now().date().isoformat(),  # revise if you version terms
                },
                "doc_hash": hash_current_document(p),
                "signed_at": timezone.now().isoformat(),
            }
            # This will also create a deposit invoice via your existing mark_signed()
            p.mark_signed(
                actor=None,
                ip=_client_ip(request),
                signature_payload=payload,
                due_date=None,
                customer_user=None,
            )
            ctx = {"proposal": p, "full_name": payload["full_name"], **_common_page_ctx(p, f"Thank you!") }
            return render(request, "proposals/signed.html", ctx)
    else:
        form = SignProposalForm()

    ctx = {"proposal": p, "form": form, **_common_page_ctx(p, f"{p.title} Proposal") }
    return render(request, "proposals/sign.html", ctx)