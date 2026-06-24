# companyApp/views/staff.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from core.utils.context import base_ctx

from userApp.models import User
from ..models import Company, ProposalDocument, RoadMap, Agreement, Invoice, CompanyUpdateLog, CompanyMember, CompanyLink, CompanyLinkType
from prospectApp.models import Prospect
from onboardingApp.models import OnboardingList
from ..forms import UpdateCompanyInfoForm, UpdateCompanyStatusForm, UpdateCompanyProjectPhaseForm, CompanyUpdateLogForm, CompanyLinkForm

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
    
    company = get_object_or_404(Company.objects.prefetch_related("members", "links", "agreements", "updates", "proposals", "roadmaps", "invoices",), pk=pk,)

    proposals_qs = company.proposals.all().order_by("-is_active", "-version", "-created_at")
    active_proposal = proposals_qs.filter(is_active=True).first()
    proposal_history = proposals_qs.filter(is_active=False)

    roadmaps_qs = company.roadmaps.all().order_by("-is_active", "-version", "-created_at")
    active_roadmap = roadmaps_qs.filter(is_active=True).first()
    roadmap_history = roadmaps_qs.filter(is_active=False)

    agreements = company.agreements.all().order_by("-uploaded_at")

    paid_invoices = company.invoices.filter(paid_at__isnull=False).order_by("-paid_at", "-created_at")

    client_links = company.links.filter(visible_to_client=True, is_active=True).select_related("link_type").order_by("link_type__sort_order", "title")
    internal_links = company.links.filter(visible_to_client=False, is_active=True).select_related("link_type").order_by("link_type__sort_order", "title")

    client_members = (
        company.members
        .filter(member_type=CompanyMember.MemberType.CLIENT, is_active=True)
        .select_related("user")
        .order_by("user__last_name", "user__first_name")
    )
    has_client_portal_users = client_members.exists()

    update_log = company.updates.all()

    onboarding_lists = OnboardingList.objects.filter(company=company, is_archived=False,).order_by("-created_at")

    link_form = CompanyLinkForm()

    title = f"{company.name} - Details"
    ctx = {"user_obj": user, "read_only": True, "company": company, "active_proposal": active_proposal, "proposal_history": proposal_history, "active_roadmap": active_roadmap, "roadmap_history": roadmap_history, "agreements": agreements, "paid_invoices": paid_invoices, "client_links": client_links, "internal_links": internal_links, "update_log": update_log, "onboarding_lists": onboarding_lists, "client_members": client_members, "has_client_portal_users": has_client_portal_users, "link_form": link_form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/view_company_detail.html", ctx)

@login_required
def company_edit(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    company = get_object_or_404(Company, pk=pk)

    if request.method == "POST":
        form = UpdateCompanyInfoForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company information updated.")
            return redirect("company_staff:company_detail", pk=company.pk)
    else:
        form = UpdateCompanyInfoForm(instance=company)

    title = f"Update {company.name}"
    ctx = {"user_obj": user, "read_only": True, "company": company, "form": form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/company_edit.html", ctx)


@login_required
def company_status(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    company = get_object_or_404(Company, pk=pk)

    if request.method == "POST":
        form = UpdateCompanyStatusForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company status updated.")
            return redirect("company_staff:company_detail", pk=company.pk)
    else:
        form = UpdateCompanyStatusForm(instance=company)

    title = f"Update Status - {company.name}"
    ctx = {"user_obj": user, "read_only": True, "company": company, "form": form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/company_status.html", ctx)


@login_required
def progress_update(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    company = get_object_or_404(Company, pk=pk)

    if request.method == "POST":
        phase_form = UpdateCompanyProjectPhaseForm(request.POST, instance=company)
        update_form = CompanyUpdateLogForm(request.POST)

        phase_ok = phase_form.is_valid()
        update_ok = update_form.is_valid()

        if phase_ok:
            phase_form.save()

        has_update_content = (
            (update_form.cleaned_data.get("title") or update_form.cleaned_data.get("body"))
            if update_ok else False
        )

        saved_update = False
        if update_ok and has_update_content:
            update = update_form.save(commit=False)
            update.company = company
            update.created_by = user
            update.save()
            saved_update = True

        if phase_ok or saved_update:
            messages.success(request, "Progress updated.")
            return redirect("company_staff:company_detail", pk=company.pk)

    else:
        phase_form = UpdateCompanyProjectPhaseForm(instance=company)
        update_form = CompanyUpdateLogForm(initial={"visible_to_client": True})

    updates = company.updates.filter(visible_to_client=True).order_by("-created_at")

    title = f"Progress Update - {company.name}"
    ctx = {"user_obj": user, "read_only": True, "company": company, "phase_form": phase_form, "update_form": update_form, "updates": updates,}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/progress_update.html", ctx)

@login_required
def add_company_link(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    company = get_object_or_404(Company, pk=pk)

    if request.method != "POST":
        return redirect("company_staff:company_detail", pk=company.pk)

    form = CompanyLinkForm(request.POST)
    if form.is_valid():
        link = form.save(commit=False)
        link.company = company
        link.created_by = user
        link.save()
        messages.success(request, "Link added.")
    else:
        messages.error(request, "Could not add link. Please check the form fields.")

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("company_staff:company_detail", pk=company.pk)

@login_required
@require_POST
def delete_company_link(request, pk: int, link_id: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    company = get_object_or_404(Company, pk=pk)
    link = get_object_or_404(CompanyLink, pk=link_id, company=company)

    link.delete()
    messages.success(request, "Link deleted.")
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("company_staff:company_detail", pk=company.pk)

@login_required
def company_resources(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not Allowed")

    company = get_object_or_404(
        Company.objects.prefetch_related(
            "links__link_type",
            "agreements",
            "proposals",
            "roadmaps",
            "invoices",
        ),
        pk=pk,
    )

    all_links = (
        company.links
        .filter(is_active=True)
        .select_related("link_type")
        .order_by("visible_to_client", "link_type__sort_order", "title")
    )

    proposals_qs = company.proposals.all().order_by("-is_active", "-version", "-created_at")
    active_proposal = proposals_qs.filter(is_active=True).first()
    proposal_history = proposals_qs.filter(is_active=False)

    roadmaps_qs = company.roadmaps.all().order_by("-is_active", "-version", "-created_at")
    active_roadmap = roadmaps_qs.filter(is_active=True).first()
    roadmap_history = roadmaps_qs.filter(is_active=False)

    agreements = company.agreements.all().order_by("-uploaded_at")
    invoices = company.invoices.all().order_by("-paid_at", "-created_at")

    link_form = CompanyLinkForm()

    title = f"{company.name} - Update Resources"
    ctx = {
        "user_obj": user,
        "read_only": True,
        "company": company,

        "link_form": link_form,
        "all_links": all_links,

        "active_proposal": active_proposal,
        "proposal_history": proposal_history,
        "active_roadmap": active_roadmap,
        "roadmap_history": roadmap_history,

        "agreements": agreements,
        "invoices": invoices,
    }
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "company_staff/company_resources.html", ctx)
