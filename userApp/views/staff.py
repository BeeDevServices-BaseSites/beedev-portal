from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from ..models import User, ClientProfile, EmployeeProfile
from prospectApp.models import Prospect
from companyApp.models import CompanyContact, Company, CompanyMembership
from core.utils.context import base_ctx
from django.db.models import Q
from django.urls import reverse

def _allowed_all_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER, User.Roles.HR}

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_upper_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER, User.Roles.HR}

@login_required
def view_all_staff(request):
    user = request.user
    if not _allowed_all_staff(request.user):
        raise PermissionDenied("Not allowed")
    
    staff = User.objects.filter(is_staff=True)
    title = 'Team Admin'
    ctx = {"user_obj": user, "staff": staff}
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/view_all_staff.html", ctx)

@login_required
def add_staff(request):
    user = request.user
    if not _allowed_management(request.user):
        raise PermissionDenied("Not allowed")
    
    url = reverse(f"admin:{User._meta.app_label}_{User._meta.model_name}_add")
    return redirect(url)

@login_required
def view_staff_profile(request, pk: int):
    user = request.user
    if not _allowed_management(request.user):
        raise PermissionDenied("Not allowed")
    
    staff = get_object_or_404(User, pk=pk)
    profile = get_object_or_404(EmployeeProfile, user=staff)
    title = f"{staff.preferred_name}'s Profile"
    ctx = {"user_obj": user, "staff": staff, "profile": profile}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "userApp/staff/view_staff_profile.html", ctx)

@login_required
def edit_staff_profile(request, pk: int):
    user = request.user
    if not _allowed_upper_management(request.user):
        raise PermissionDenied("Not Allowed")
    
    url = reverse("admin:userApp_user_change", args=[pk])
    return redirect(url)

@login_required
def view_all_clients(request):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")
    
    contacts = (
        User.objects
        .filter(role=User.Roles.CLIENT, company_memberships__is_active=True)
        .distinct()
        .order_by('first_name', 'last_name', 'username')
    )
    prospects = (
        Prospect.objects
        .exclude(status__in=[Prospect.Status.WON, Prospect.Status.LOST, Prospect.Status.UNSUB])
        .filter(Q(company__isnull=True) | Q(company__status=Company.Status.PROSPECT))
        .order_by('full_name', 'company_name')
    )
    lost = Prospect.objects.filter(status="LST").order_by('full_name', 'company_name')
    dnc  = Prospect.objects.filter(status="UNS").order_by('full_name', 'company_name')

    won = Prospect.objects.filter(status=Prospect.Status.WON, company__isnull=False).exclude(
        company__memberships__is_active=True,
        company__memberships__user__role=User.Roles.CLIENT,
    )
    all = Prospect.objects.all()
    print(all)
    title = 'Contacts Admin'
    ctx = {"user_obj": user, "contacts": contacts, "prospects": prospects, "lost": lost, "dnc": dnc, "won": won}
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/view_all_contacts.html", ctx)

@login_required
def view_client_profile(request, pk: int):
    user = request.user
    if not _allowed_management(request.user):
        raise PermissionDenied("Not allowed")
    
    client = get_object_or_404(User, pk=pk)
    profile = get_object_or_404(ClientProfile, user=client)
    company_membership = get_object_or_404(CompanyMembership, user_id=pk)
    company = get_object_or_404(Company, pk=company_membership.company_id)
    title = f"{client.preferred_name}'s Profile"
    print('client:', client.first_name, 'profile:', profile, 'company:', company)
    ctx = {"user_obj": user, "client": client, "profile": profile, "company": company}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "userApp/staff/view_client_profile.html", ctx)