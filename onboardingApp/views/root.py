from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx

from userApp.models import User
from ..models import OnboardingList


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
    
    staff = OnboardingList.objects.filter(kind="STAFF").exclude(is_archived=True)
    client = OnboardingList.objects.filter(kind="CLIENT").exclude(is_archived=True)

    archived = OnboardingList.objects.exclude(is_archived=False)

    title = "Onboarding Admin"
    ctx = {"user_obj": user, "read_only": True, "staff": staff, "client": client, "archived": archived}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "onboardingApp/onboard_home.html", ctx)

@login_required
def add_onboard_list(request):
    pass