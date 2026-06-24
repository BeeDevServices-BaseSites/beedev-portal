from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx
from django.db.models import Q, Count
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
    won = (Prospect.objects
           .filter(status=Prospect.Status.WON, company__isnull=False)
           .exclude(company__members__is_active=True, company__members__member_type=CompanyMember.MemberType.CLIENT, company__members__user__role=User.Roles.CLIENT,)
           .select_related("company")
           .order_by("full_name", "company_name")
    )

    won_company_ids = list(won.values_list("company__id", flat=True))
    client_onboarding_lists = ( OnboardingList.objects
                               .filter(kind='CLIENT', is_archived=False, company_id__in=won_company_ids)
                               .annotate(total_items_count=Count("items", distinct=True), completed_items_count=Count("items", filter=Q(items__is_completed=True), distinct=True),)
                               .select_related("company"))
    
    onboarding_by_company_id = {ol.company_id: ol for ol in client_onboarding_lists}

    title = 'Contacts Admin'
    ctx = {"user_obj": user, "contacts": contacts, "prospects": prospects, "won": won, "lost": lost, "onboarding": onboarding_by_company_id}
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