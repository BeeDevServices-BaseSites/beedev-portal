# proposalApp/public.py
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseForbidden
from ..models import Proposal

def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def public_proposal_view(request, token: str):
    proposal = get_object_or_404(Proposal, sign_token=token)

    # Optional: token expiry gate
    if proposal.token_expires_at and timezone.now() > proposal.token_expires_at:
        # You could render a friendlier page with a "request a new link" CTA
        return render(request, "proposals/token_expired.html", {"proposal": proposal}, status=403)

    # Log "viewed" once; subsequent hits won’t change the timestamp
    proposal.mark_viewed(ip=_client_ip(request))

    # Gather display data (client-facing only)
    items = proposal.line_items.all().order_by("sort_order", "pk")
    notes  = proposal.notes.filter(is_visible_to_client=True).order_by("sort_order", "pk")
    summary = getattr(proposal, "summary", None)

    ctx = {
        "proposal": proposal,
        "company": proposal.company,   # convenience
        "items": items,
        "notes": notes,
        "summary_md": getattr(summary, "body_md", ""),
        "can_download_pdf": bool(proposal.pdf),
    }
    return render(request, "proposals/public_view.html", ctx)
