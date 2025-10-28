from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils.context import CommonContextMixin, base_ctx
from ..forms import PortalAuthForm
from django.db.models import Prefetch, Max
from ..models import User
from proposalApp.models import Proposal, ProposalDraft, ProposalEvent
from projectApp.models import Project
from companyApp.models import CompanyMembership
import logging
log = logging.getLogger(__name__)


class PortalLogin(CommonContextMixin,LoginView):
    template_name = "userApp/index.html"
    redirect_authenticated_user = True
    form_class = PortalAuthForm
    common_title = "Portal"

def _allowed_all_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER, User.Roles.HR}

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_upper_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER, User.Roles.HR}

@login_required
def post_login(request):
    u = request.user
    if getattr(u, "is_staff", False) or getattr(u, "role", None) == "EMPLOYEE":
        return redirect("admin:index")

    return redirect("userApp:client_home")

@login_required
def staff_home(request):
    return redirect("admin:index")

@login_required
def employee_home(request):
    user = request.user
    if not _allowed_all_staff(request.user):
        raise redirect("userApp:client_home")
    
    drafts = ProposalDraft.objects.all()
    proposals_qs = (
        Proposal.objects
        .select_related("company")
        .annotate(last_event_at=Max("events__at"))
        .prefetch_related(
            Prefetch(
                "events",
                queryset=ProposalEvent.objects.select_related("actor").order_by("-at", "pk")
            )
        )
        .order_by("-last_event_at", "-created_at")
    )
    proposals = list(proposals_qs)
    last_events_by_id = {
        p.id: (p.events.all()[0] if p.events.all() else None)
        for p in proposals
    }
    users = User.objects.all()
    projects = Project.objects.all()
    
    if _allowed_upper_management(request.user):
        admin_drafts = drafts.filter(approval_status="SUBMITTED")
        drafts = drafts.exclude(approval_status__in=["SUBMITTED", "CONVERTED"])
        dash = {"drafts": drafts, "admin_drafts": admin_drafts, "proposals": proposals, "users": users, "last_events_by_id": last_events_by_id}
    elif _allowed_staff(request.user): 
        drafts = drafts.filter(created_by_id=user.id)
        proposals = proposals.filter(created_by_id=user.id)
        dash = {"drafts": drafts, "proposals": proposals, "last_events_by_id": last_events_by_id}
    print(dash, request.user.role)
    ctx = {"user_obj": user, "read_only": True, 'dash': dash}
    title = "BeeDev Services Work Dashboard"
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/employee_home.html", ctx)

@login_required
def client_home(request):
    u = request.user
    memberships = (
        CompanyMembership.objects
        .filter(user=u, is_active=True)
        .select_related("company")
    )
    companies_info = []
    company = ''
    if not memberships.exists():
        print(f"[DASH] {u.email} has no active company memberships")
    else:
        for m in memberships:
            c = m.company
            company = m.company

            # All proposals for the company
            props_all = (
                Proposal.objects
                .filter(company=c)
                .only("id", "title", "created_at")
                .order_by("-created_at")
            )

            # Proposals explicitly shared with this user (via ProposalViewer)
            props_shared = (
                Proposal.objects
                .filter(company=c, allowed_viewers__user=u)
                .only("id", "title", "created_at")
                .distinct()
                .order_by("-created_at")
            )

            companies_info.append({
                "company": c,
                "proposals_all": list(props_all),
                "proposals_shared": list(props_shared),
            })
    ctx = {
        "user_name": u.get_full_name() or u.username,
        "companies_info": companies_info,
        "company": company
    }
    title = "Dashboard"
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/client/client_home.html", ctx)