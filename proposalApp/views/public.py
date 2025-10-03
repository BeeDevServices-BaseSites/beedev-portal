# proposalApp/public.py
from django.shortcuts import get_object_or_404, render
from django.http import FileResponse, Http404
from django.utils import timezone
from django.db.models import Prefetch
from django.conf import settings

from ..models import Proposal, ProposalLineItem, ProposalEvent
from ..pdf import generate_proposal_pdf

def _client_ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))

def _guard_token(proposal: Proposal):
    if proposal.token_expires_at and timezone.now() > proposal.token_expires_at:
        raise Http404("Link expired")

def public_proposal_view(request, token: str):
    proposal = get_object_or_404(
        Proposal.objects.select_related("company").prefetch_related(
            Prefetch("line_items", queryset=ProposalLineItem.objects.select_related("job_rate", "base_setting").order_by("sort_order", "pk"))
        ),
        sign_token=token,
    )
    _guard_token(proposal)
    first = proposal.mark_viewed(ip=_client_ip(request), actor=None)
    return render(request, "proposals/public_view.html", {
        "proposal": proposal,
        "items": list(proposal.line_items.all()),
        "first_view": first,
    })

def public_proposal_pdf(request, token: str):
    proposal = get_object_or_404(Proposal, sign_token=token)
    _guard_token(proposal)

    if not proposal.pdf:
        base_url = request.build_absolute_uri("/")
        generate_proposal_pdf(proposal, request=request, base_url=base_url, force=True)

    if not proposal.pdf:
        raise Http404("PDF not available")

    return FileResponse(proposal.pdf.open("rb"), content_type="application/pdf")
