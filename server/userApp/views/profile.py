from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx

from ..models import User, EmployeeProfile


# -------------------------------------------------------------------
# Permission helpers
# -------------------------------------------------------------------
def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_upper_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

# -------------------------------------------------------------------
# Staff Profile Functions
# -------------------------------------------------------------------
@login_required
def staff_profile(request):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")
    
    profile, _ = EmployeeProfile.objects.get_or_create(user=user)
    
    title = f"{user.preferred_name}'s Profile"
    ctx = {"user_obj": user, "profile": profile, "read_only": True}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "userApp/staff/view_staff_profile.html", ctx)

# -------------------------------------------------------------------
# Client Profile Functions
# -------------------------------------------------------------------