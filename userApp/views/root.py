from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from core.utils.context import CommonContextMixin, base_ctx
from django.db.models import Prefetch, Max
from ..models import User
import logging
log = logging.getLogger(__name__)


class PortalLogin(CommonContextMixin,LoginView):
    template_name = "userApp/index.html"
    redirect_authenticated_user = True
    common_title = "Portal"

    def get_success_url(self):
        return reverse("userApp:post_login")

def _allowed_all_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.OWNER}

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.OWNER}


@login_required
def post_login(request):
    u = request.user

    if _allowed_management(u):
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
    
    users = User.objects.all()
    
    if _allowed_management(request.user):
        dash = {"users": users}

    else: 
        dash = {}
        
    ctx = {"user_obj": user, "read_only": True, 'dash': dash}
    title = "BeeDev Services Work Dashboard"
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