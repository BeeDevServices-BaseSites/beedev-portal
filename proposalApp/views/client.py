from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from ..models import Proposal, ProposalLineItem
from companyApp.models import CompanyMembership
from core.utils.context import base_ctx
from userApp.models import User

import logging
log = logging.getLogger(__name__)

def _allowed_users(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.CLIENT}

@login_required
def view_all_client_proposals(request):
    user = request.user
    if not _allowed_users(request.user):
        raise PermissionDenied("Not allowed")
    
    memberships = (
        CompanyMembership.objects
        .filter(user=user, is_active=True)
        .select_related("company")
    )
    proposals = []
    if not memberships.exists():
        log.info("[DASH] no active company memberships", user.email)
    else:
        for m in memberships:
            c = m.company
            
            props_all = (
                Proposal.objects
                .filter(company=c)
                .order_by("-created_at")
            )
            props_shared = (
                Proposal.objects
                .filter(company=c, allowed_viewers__user=user)
                .distinct()
                .order_by("-created_at")
            )
            props_signed = (
                Proposal.objects
                .filter(company=c, signed_at__isnull=False)
                .order_by("-signed_at", "-created_at")
            )
            props_awaiting_signature = (
                Proposal.objects
                .filter(company=c, signed_at__isnull=True, sent_at__isnull=False)
                .order_by("-sent_at", "-created_at")
            )
            proposals.append({
                "company": c,
                "proposals_all": list(props_all),
                "proposals_shared": list(props_shared),
                "signed": list(props_signed),
                "due": list(props_awaiting_signature)
            })
    title = "Proposals"
    ctx = {"user_obj": user, "read_only": True, "proposals": proposals}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_client/view_all_proposals.html", ctx)