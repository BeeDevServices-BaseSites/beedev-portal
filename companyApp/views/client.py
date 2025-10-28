from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch, Count, Sum, Q
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx
from ..models import Company, CompanyContact, CompanyLink
from proposalApp.models import Proposal, ProposalEvent
from userApp.models import User


def _allowed_users(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.CLIENT}

@login_required
def view_my_company_detail(request, pk: int):
    user = request.user
    if not _allowed_users(request.user):
        raise PermissionDenied("Not allowed")
    
    company = get_object_or_404(Company, pk=pk)
    contacts = CompanyContact.objects.filter(company=company).order_by("name")
    links = CompanyLink.objects.filter(company=company).order_by("id")

    proposals = (company.simple_proposals.select_related("created_by").prefetch_related("line_items", "applied_discounts", "recipients", "events").order_by("created_at"))

    proposal_stats = proposals.aggregate(count=Count("id"), signed=Count("id", filter=Q(signed_at__isnull=False)), pending=Count("id", filter=Q(signed_at__isnull=True)), total_amount=Sum("amount_total"))

    recent_events = (ProposalEvent.objects.filter(proposal__company=company).select_related("proposal", "actor").order_by("-at")[:10])

    title = f"{company.name} - Details"
    ctx = {"user_obj": user, "read_only": True, "company": company, "contacts":contacts, "links": links, "proposals": proposals, "proposal_stats": proposal_stats, "recent_events": recent_events}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_client/view_my_company_detail.html", ctx)