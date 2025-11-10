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

    if _allowed_upper_management(u):
        return redirect("admin:index")
    
    if _allowed_all_staff(u) or getattr(u, "is_staff", False) or getattr(u, "is_superuser", False):
        return redirect("userApp:employee_home")

    return redirect("userApp:client_home")

@login_required
def staff_home(request):
    return redirect("admin:index")

@login_required
def employee_home(request):
    user = request.user
    if not _allowed_all_staff(request.user):
        return redirect("userApp:client_home")
    
    drafts_qs = ProposalDraft.objects.all()
    events_qs = ProposalEvent.objects.select_related("actor").order_by("-at", "pk")
    proposals_qs = (
        Proposal.objects
        .select_related("company")
        .annotate(last_event_at=Max("events__at"))
        .prefetch_related(Prefetch("events", queryset=events_qs))
        .order_by("-last_event_at", "-created_at")
    )
    users = User.objects.all()
    projects = Project.objects.all()
    
    if _allowed_upper_management(request.user):
        admin_drafts = drafts_qs.filter(approval_status="SUBMITTED")
        drafts_qs = drafts_qs.exclude(approval_status__in=["SUBMITTED", "CONVERTED"])
        proposals = list(proposals_qs)
        last_events_by_id = {
            p.id: (p.events.all()[0] if p.events.all() else None)
            for p in proposals
        }
        dash = {"drafts": drafts_qs, "admin_drafts": admin_drafts, "proposals": proposals, "users": users, "last_events_by_id": last_events_by_id, "projects": projects}

    else: 
        drafts_qs = drafts_qs.filter(created_by_id=user.id)
        proposals_qs = proposals_qs.filter(created_by_id=user.id)
        proposals = list(proposals_qs)
        last_events_by_id = {
            p.id: (p.events.all()[0] if p.events.all() else None)
            for p in proposals
        }
        dash = {"drafts": drafts_qs, "proposals": proposals, "last_events_by_id": last_events_by_id, "projects": projects}
        
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
        log.info("[DASH] no active company memberships", u.email)
    else:
        for m in memberships:
            c = m.company
            company = m.company

            props_all = (
                Proposal.objects
                .filter(company=c)
                .only("id", "title", "created_at")
                .order_by("-created_at")
            )

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