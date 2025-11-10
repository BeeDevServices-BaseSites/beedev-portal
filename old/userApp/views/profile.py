from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from ..models import ClientProfile, EmployeeProfile
from core.utils.context import base_ctx
from django.contrib.auth import get_user_model
from companyApp.models import CompanyMembership

@login_required
def view_client_profile(request, pk: int | None = None):
    user = request.user
    U = get_user_model()

    if pk is None:
        if getattr(user, 'role', None) != user.Roles.CLIENT:
            raise PermissionDenied("This page is for clients only")
        target_user = user
        read_only = False
    else:
        allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER, user.Roles.HR}
        if getattr(user, 'role', None) not in allowed_roles:
            raise PermissionDenied("Not allowed")
        target_user = get_object_or_404(U, pk=pk)
        if getattr(target_user, 'role', None) != target_user.Roles.CLIENT:
            raise PermissionDenied("Target user is not a client")
        read_only = True

    profile, _ = ClientProfile.objects.get_or_create(user=target_user)
    membership = (
        CompanyMembership.objects
        .select_related("company")
        .filter(user=target_user)
        .order_by("role")
        .first()
    )
    company = membership.company if membership else None

    title = f"{target_user.preferred_name} Profile"
    ctx = {"user_obj": target_user, "profile": profile, "company": company, "read_only": read_only}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "userApp/view_client_profile.html", ctx)

@login_required
def view_employee_profile(request):
    user = request.user
    allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER, user.Roles.HR}
    if getattr(user, "role", None) not in allowed_roles:
        raise PermissionDenied("Not allowed")

    if user.role == user.Roles.EMPLOYEE:
        profile, _ = EmployeeProfile.objects.get_or_create(user=user)
    else:
        profile = getattr(user, "employee_profile", None)
        if not profile:
            raise PermissionDenied("No employee profile found")

    title = f"{user.preferred_name} Profile"
    ctx = {"user_obj": user, "profile": profile, "read_only": True}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "userApp/staff/view_employee_profile.html", ctx)
