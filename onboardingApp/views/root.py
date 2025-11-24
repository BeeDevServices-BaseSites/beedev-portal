from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx

from userApp.models import User


# -------------------------------------------------------------------
# Permission Helpers
# -------------------------------------------------------------------

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.ADMIN, User.Roles.OWNER}

# -------------------------------------------------------------------
# Main Functions
# -------------------------------------------------------------------

@login_required
def onboard_home(request):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")
    
    title = "Onboarding Admin"
    ctx = {"user_obj": user, "read_only": True}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "onboardingApp/onboard_home.html", ctx)