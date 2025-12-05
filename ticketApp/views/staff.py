# ticketApp/views/staff.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx

from userApp.models import User
from ..models import (Ticket,)
from companyApp.models import Company


# -------------------------------------------------------------------
# Permission helpers
# -------------------------------------------------------------------
def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_upper_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

# -------------------------------------------------------------------
# Main Functions
# -------------------------------------------------------------------

def staff_ticket_home(request):
    user = request.user
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not Allowed")
    
    tickets = Ticket.objects.all()

    title = "Ticket Admin"
    ctx = {"user_obj": user, "read_only": True, "tickets": tickets}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "ticket_staff/staff_ticket_home.html", ctx)