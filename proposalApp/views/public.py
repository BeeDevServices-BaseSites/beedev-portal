# proposalApp/public.py
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.html import linebreaks
from django.views.decorators.http import require_http_methods
from ..models import Proposal
from core.utils.context import base_ctx

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
