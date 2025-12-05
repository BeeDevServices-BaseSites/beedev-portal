from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from core.utils.context import CommonContextMixin, base_ctx
from django.db.models import Prefetch, Max
from django.db.models import Q, Count
from django.utils import timezone


from ..models import User
from companyApp.models import Company
from prospectApp.models import Prospect
from ticketApp.models import Ticket
from onboardingApp.models import OnboardingList, OnboardingListItem
import logging
log = logging.getLogger(__name__)


class PortalLogin(CommonContextMixin,LoginView):
    template_name = "userApp/index.html"
    redirect_authenticated_user = True
    common_title = "Portal"

    def get_success_url(self):
        return reverse("userApp:post_login")

def _allowed_all_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.OWNER}

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.OWNER}


@login_required
def post_login(request):
    u = request.user

    if _allowed_management(u):
        return redirect("admin:index")
    
    if _allowed_all_staff(u) or getattr(u, "is_staff", False) or getattr(u, "is_superuser", False):
        return redirect("userApp:employee_home")

    return redirect("userApp:client_home")

@login_required
def employee_home(request):
    return redirect("admin:index")

@login_required
def staff_home(request):
    user = request.user
    if not _allowed_all_staff(request.user):
        return redirect("userApp:client_home")
    
    today = timezone.now()
    total_companies = Company.objects.filter(status__in=[Company.Status.PROSPECT, Company.Status.ACTIVE]).count()

    total_prospects = Prospect.objects.exclude(status=Prospect.Status.CLOSED_LOST).count()

    open_tickets = Ticket.objects.filter(status__in=[Ticket.Status.NEW, Ticket.Status.OPEN, Ticket.Status.INPROGRESS, Ticket.Status.PENDING]).count()

    my_open_tickets = Ticket.objects.filter(assigned_to=user, status__in=[Ticket.Status.NEW, Ticket.Status.OPEN, Ticket.Status.INPROGRESS, Ticket.Status.PENDING,],).count()

    prospects_needing_followup = (Prospect.objects.filter(Q(next_follow_up_at__lte=today) | Q(next_follow_up_at__isnull=True),).exclude(status__in=[Prospect.Status.WON, Prospect.Status.CLOSED_LOST]).order_by("next_follow_up_at", "full_name", "company_name")[:10])

    recent_companies = Company.objects.order_by("-updated_at")[:10]

    my_onboarding_items = (OnboardingListItem.objects.select_related("onboarding_list", "onboarding_list__company", "onboarding_list__staff_user").filter(is_completed=False, onboarding_list__is_archived=False,).order_by("onboarding_list__created_at", "sort_order")[:10])

    dash = {
        "metrics": {
            "total_companies": total_companies,
            "total_prospects": total_prospects,
            "open_tickets": open_tickets,
            "my_open_tickets": my_open_tickets,
        },
        "prospects_needing_followup": prospects_needing_followup,
        "recent_companies": recent_companies,
        "my_onboarding_items": my_onboarding_items,
    }

    ctx = {"user_obj": user, "read_only": True, "dash": dash}
    title = "BeeDev Services Work Dashboard"
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/staff/staff_home.html", ctx)

@login_required
def client_home(request):
    u = request.user

    ctx = {
        "user_name": u.get_full_name() or u.username,
    }
    title = "Dashboard"
    ctx.update(base_ctx(request, title=title))
    ctx['page_heading'] = title
    return render(request, "userApp/client/client_home.html", ctx)