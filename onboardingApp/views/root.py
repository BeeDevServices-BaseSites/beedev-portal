# onboardingApp/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction

from core.utils.context import base_ctx
from userApp.models import User
from ..models import OnboardingList, OnboardingListItem


# -------------------------------------------------------------------
# Permission helpers
# -------------------------------------------------------------------
def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.STAFF, User.Roles.ADMIN, User.Roles.OWNER}

def _is_owner_admin(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.OWNER, User.Roles.ADMIN}


def _is_staff_role(u: User) -> bool:
    return u.is_active and u.role == User.Roles.STAFF


def _is_client_role(u: User) -> bool:
    return u.is_active and u.role == User.Roles.CLIENT


def _can_view_list(u: User, lst: OnboardingList) -> bool:
    if not u.is_authenticated:
        return False

    if _is_owner_admin(u):
        return True

    if lst.management_only:
        return False

    if lst.kind == OnboardingList.Kind.STAFF:
        if _is_staff_role(u) and lst.staff_user_id == u.id:
            return True
        if _is_staff_role(u):
            return True
        return False

    if lst.kind == OnboardingList.Kind.CLIENT:
        if _is_staff_role(u):
            return True
        if _is_client_role(u) and lst.visible_to_subject:
            return True

    return False


def _can_edit_items(u: User, lst: OnboardingList) -> bool:
    if not u.is_authenticated:
        return False

    if _is_owner_admin(u):
        return True

    if lst.management_only:
        return False

    if lst.kind == OnboardingList.Kind.STAFF:
        if _is_staff_role(u) and lst.staff_user_id == u.id:
            return True
        return False

    if lst.kind == OnboardingList.Kind.CLIENT:
        if _is_staff_role(u):
            return True
        if _is_client_role(u) and lst.visible_to_subject:
            return True

    return False

# -------------------------------------------------------------------
# Onboarding Home (list all relevant checklists)
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


# -------------------------------------------------------------------
# Onboarding List Detail + item check/uncheck
# -------------------------------------------------------------------

@login_required
@transaction.atomic
def onboarding_list_detail(request, pk: int):
    lst = get_object_or_404(
        OnboardingList.objects.select_related("staff_user", "company"),
        pk=pk,
    )
    user = request.user

    if not _can_view_list(user, lst):
        raise PermissionDenied("Not allowed")

    items = list(lst.items.all().order_by("sort_order", "pk"))
    can_edit = _can_edit_items(user, lst)

    if request.method == "POST":
        if not can_edit:
            raise PermissionDenied("You are not allowed to update this checklist.")

        posted_done_ids = set()
        posted_resource_ids = set()

        for key in request.POST.keys():
            if key.startswith("item-"):
                try:
                    posted_done_ids.add(int(key.split("-", 1)[1]))
                except ValueError:
                    pass
            if key.startswith("resource-"):
                try:
                    posted_resource_ids.add(int(key.split("-", 1)[1]))
                except ValueError:
                    pass
        
        blocked_titles = []

        for item in items:
            wants_done = item.pk in posted_done_ids

            if item.requires_resource:
                resource_checked = item.pk in posted_resource_ids
                if item.resource_added != resource_checked:
                    item.resource_added = resource_checked
                    item.save(update_fields=["resource_added", "updated_at"])

            if wants_done and item.requires_resource and not item.resource_added:
                blocked_titles.append(item.title)
                wants_done = False
            
            if wants_done and not item.is_completed:
                try:
                    item.mark_complete(user=user)
                except ValidationError:
                    blocked_titles.append(item.title)
            
            elif not wants_done and item.is_completed:
                item.is_completed = False
                item.completed_at = None
                item.completed_by = None
                item.save(
                    update_fields=[
                        "is_completed",
                        "completed_at",
                        "completed_by",
                        "updated_at",
                    ]
                )
        
        if blocked_titles:
            messages.error(
                request,
                "Some tasks require a resource to be added before they can be completed: "
                + ", ".join(f'"{t}"' for t in blocked_titles)
            )
        else:
            messages.success(request, "Onboarding checklist updated.")

        lst.refresh_completion_status(save=True)

        return redirect("onboarding:list_detail", pk=lst.pk)

    # GET: render page
    title = lst.title or "Onboarding Checklist"
    ctx = {
        "list_obj": lst,
        "items": items,
        "can_edit": can_edit,
    }
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "onboardingApp/list_detail.html", ctx)


@login_required
def add_onboard_list(request):
    pass