from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx

from userApp.models import User
from ..models import Company
from prospectApp.models import Prospect

# -------------------------------------------------------------------
# Permission Helpers
# -------------------------------------------------------------------

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.ADMIN, User.Roles.OWNER}

# -------------------------------------------------------------------
# Main Functions
# -------------------------------------------------------------------

@login_required
def company_home(request):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")
    
    companies = Company.objects.all()
    prospects = Prospect.objects.exclude(status="WON")

    title = "Company Admin"
    ctx = {"user_obj": user, "read_only": True, "companies": companies, "prospects": prospects}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/company_home.html", ctx)

@login_required
def view_company_detail(request, pk: int):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not Allowed")
    
    company = get_object_or_404(Company, pk=pk)

    title = f"{company.name} - Details"
    ctx = {"user_obj": user, "read_only": True, "company": company}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/view_company_detail.html", ctx)