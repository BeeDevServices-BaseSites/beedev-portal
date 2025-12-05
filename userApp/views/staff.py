from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx
from django.db.models import Q
from django.urls import reverse

from ..models import User
from prospectApp.models import Prospect
from companyApp.models import Company, CompanyMember
from onboardingApp.models import OnboardingList


# -------------------------------------------------------------------
# Permission helpers
# -------------------------------------------------------------------
def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_upper_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

# -------------------------------------------------------------------
# Prospects
# -------------------------------------------------------------------
@login_required
def view_all_clients(request):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")
    
    onboarding = OnboardingList.objects.filter(kind="CLIENT").exclude(is_archived=True)
    
    contacts = (
        User.objects
        .filter(role=User.Roles.CLIENT, company_memberships__is_active=True, company_memberships__member_type=CompanyMember.MemberType.CLIENT,)
        .distinct()
        .order_by('first_name', 'last_name', 'username')
    )
    prospects = (
        Prospect.objects
        .exclude(status__in=[Prospect.Status.WON, Prospect.Status.CLOSED_LOST])
        .filter(Q(company__isnull=True) | Q(company__status=Company.Status.PROSPECT))
        .order_by('full_name', 'company_name')
    )
    lost = Prospect.objects.filter(status=Prospect.Status.CLOSED_LOST).order_by('full_name', "company_name")
    won = Prospect.objects.filter(status=Prospect.Status.WON, company__isnull=False).exclude(
        company__members__is_active=True,
        company__members__member_type=CompanyMember.MemberType.CLIENT, company__members__user__role=User.Roles.CLIENT,
    )
    all = Prospect.objects.all()
    print(all)
    title = 'Contacts Admin'
    ctx = {"user_obj": user, "contacts": contacts, "prospects": prospects, "won": won, "lost": lost, "onboarding": onboarding}
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/view_all_contacts.html", ctx)

@login_required
def team_home(request):
    user = request.user
    if not _allowed_upper_management(request.user):
        raise PermissionDenied("Not allowed")
    
    title = 'Team Admin'
    ctx = {"user_obj": user, }
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/team_home.html", ctx)