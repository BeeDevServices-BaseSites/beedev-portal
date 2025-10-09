from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404
from core.utils.context import base_ctx
from ..models import Invoice
from userApp.models import User

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

@login_required
def invoice_home(request):
    user = request.user
    if not _allowed_management(request.user):
        raise PermissionDenied("Not allowed")
    
    invoices = Invoice.objects.all()
    unpaid = Invoice.objects.exclude(status__in=["PAID"])
    paid = Invoice.objects.filter(status="PAID")

    title = "Invoice Admin"
    ctx = {"user_obj": user, "read_only": True, "invoices": invoices, "unpaid": unpaid, "paid": paid}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "invoice_staff/invoice_home.html", ctx)