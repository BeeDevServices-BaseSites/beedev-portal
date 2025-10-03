from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from ..models import Proposal, ProposalLineItem
from core.utils.context import base_ctx
from userApp.models import User

def _allowed_users(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.CLIENT}

@login_required
def view_all_client_proposals(request):
    user = request.user
    if not _allowed_users(request.user):
        raise PermissionDenied("Not allowed")
    
    title = "Proposals"
    ctx = {"user_obj": user, "read_only": True}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_client/view_all_proposals.html", ctx)