from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.utils.context import CommonContextMixin, base_ctx
from ..forms import PortalAuthForm
from ..models import User
from proposalApp.models import Proposal, ProposalDraft
from projectApp.models import Project

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

    # Otherwise go to client dashboard
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
    proposals = Proposal.objects.all()
    users = User.objects.all()
    projects = Project.objects.all()
    
    if _allowed_upper_management(request.user):
        drafts = drafts.filter(approval_status="SUBMITTED")
        dash = {"drafts": drafts, "proposals": proposals, "users": users}
    elif _allowed_staff(request.user): 
        drafts = drafts.filter(created_by_id=user.id)
        proposals = proposals.filter(created_by_id=user.id)
        dash = {"drafts": drafts, "proposals": proposals}

    ctx = {"user_obj": user, "read_only": True, 'dash': dash}
    title = "Dashboard"
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/employee_home.html", ctx)

@login_required
def client_home(request):
    u = request.user
    ctx = {
        "user_name": u.get_full_name() or u.username,
    }
    title = "Dashboard"
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/client/client_home.html", ctx)