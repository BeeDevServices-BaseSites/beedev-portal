# prospectApp/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.utils import timezone

from core.utils.context import base_ctx
from ..models import Prospect, ProspectNote
from ..forms import (
    ProspectForm,
    ProspectEditForm,
    ProspectStatusForm,
    ProspectNoteQuickForm,
)
from userApp.models import User
from companyApp.models import Company
# from onboardingApp.models import OnboardingList


# -------------------------------------------------------------------
# Permission helpers
# -------------------------------------------------------------------

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {
        User.Roles.OWNER,
        User.Roles.ADMIN,
        User.Roles.STAFF,
    }


# -------------------------------------------------------------------
# Add Prospect
# -------------------------------------------------------------------

@login_required
def add_prospect(request):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    if request.method == "POST":
        form = ProspectForm(request.POST)
        if form.is_valid():
            prospect: Prospect = form.save(commit=False)
            prospect.created_by = user
            prospect.updated_by = user
            prospect.save()
            messages.success(request, "Prospect added successfully.")
            return redirect("userApp:view_all_clients")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProspectForm()

    title = "Add Prospect"
    ctx = {"form": form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/add_prospect.html", ctx)


# -------------------------------------------------------------------
# View single Prospect + notes
# -------------------------------------------------------------------

@login_required
def view_prospect(request, pk: int):
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")

    prospect = get_object_or_404(Prospect, pk=pk)
    notes = ProspectNote.objects.filter(prospect=prospect)

    name_for_title = (
        prospect.full_name
        or prospect.company_name
        or prospect.email
        or f"Prospect #{prospect.pk}"
    )
    title = f"{name_for_title} — Prospect"

    ctx = {
        "user_obj": request.user,
        "prospect": prospect,
        "notes": notes,
    }
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/view_one_prospect.html", ctx)


# -------------------------------------------------------------------
# Edit Prospect core details
# -------------------------------------------------------------------

@login_required
def edit_prospect(request, pk: int):
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")

    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method == "POST":
        form = ProspectEditForm(request.POST, instance=prospect)
        if form.is_valid():
            obj: Prospect = form.save(commit=False)
            obj.email = (obj.email or "").strip().lower()
            obj.updated_by = request.user
            obj.save()
            messages.success(request, "Prospect updated.")
            return redirect("prospects:prospect_edit", pk=prospect.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProspectEditForm(instance=prospect)

    name_for_title = (
        prospect.full_name
        or prospect.company_name
        or prospect.email
        or f"Prospect #{prospect.pk}"
    )
    title = f"Edit Prospect — {name_for_title}"

    ctx = {
        "user_obj": request.user,
        "prospect": prospect,
        "form": form,
    }
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/prospect_edit.html", ctx)


# -------------------------------------------------------------------
# Update status + optional quick note
# -------------------------------------------------------------------

@login_required
@transaction.atomic
def update_prospect_status(request, pk: int):
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")

    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method == "POST":
        form = ProspectStatusForm(request.POST, instance=prospect)
        note_form = ProspectNoteQuickForm(request.POST)

        if form.is_valid() and note_form.is_valid():
            old_status = prospect.status

            changed_fields = list(form.changed_data)
            prospect = form.save(commit=False)
            prospect.updated_by = request.user
            if changed_fields:
                try:
                    prospect.save(
                        update_fields=list(
                            set(changed_fields + ["updated_by", "updated_at"])
                        )
                    )
                except TypeError:
                    prospect.save()
            else:
                prospect.save()

            subj = (note_form.cleaned_data.get("subject") or "").strip()
            body = (note_form.cleaned_data.get("body_md") or "").strip()
            pinned = bool(note_form.cleaned_data.get("is_pinned"))
            if subj or body:
                ProspectNote.objects.create(
                    prospect=prospect,
                    subject=subj or "Note",
                    body_md=body,
                    is_pinned=pinned,
                    created_by=request.user,
                )
                messages.success(request, "Note added to prospect history.")

            new_status = prospect.status

            created_or_updated_company = None
            company = prospect.linked_company

            if new_status == Prospect.Status.CONSULT_PENDING:
                company = prospect.create_or_update_company(actor=request.user)

                updates = []
                if company.status != Company.Status.PROSPECT:
                    company.status = Company.Status.PROSPECT
                    updates.append("status")
                if company.pipeline_status != Company.PipelineStatus.HOLDING:
                    company.pipeline_status = Company.PipelineStatus.HOLDING
                    updates.append("pipeline_status")
                if company.work_status != Company.WorkStatus.NONE:
                    company.work_status = Company.WorkStatus.NONE
                    updates.append("work_status")

                if updates:
                    company.save(update_fields=updates + ["updated_at"])
                created_or_updated_company = company

            elif new_status == Prospect.Status.WON:
                company = prospect.create_or_update_company(actor=request.user)

                updates = []
                if company.status != Company.Status.ACTIVE:
                    company.status = Company.Status.ACTIVE
                    updates.append("status")
                if company.pipeline_status == Company.PipelineStatus.HOLDING:
                    company.pipeline_status = Company.PipelineStatus.NEW
                    updates.append("pipeline_status")

                if updates:
                    company.save(update_fields=updates + ["updated_at"])
                created_or_updated_company = company

            # elif new_status == Prospect.Status.CLOSED_LOST and company:
            #     OnboardingList.objects.filter(
            #         company=company,
            #         is_archived=False,
            #     ).update(
            #         is_archived=True,
            #         completed_at=timezone.now(),
            #     )

            if created_or_updated_company is not None:
                if old_status != new_status:
                    messages.success(
                        request,
                        f"Status updated ({old_status or '-'} → {new_status or '-'}) "
                        f"and Company '{created_or_updated_company.name}' synced."
                    )
                else:
                    messages.success(
                        request,
                        f"Company '{created_or_updated_company.name}' created/updated for this prospect."
                    )
            elif changed_fields:
                messages.success(
                    request,
                    f"Status/fields updated ({', '.join(changed_fields)}) — "
                    f"status {old_status or '-'} → {new_status or '-'}"
                )
            else:
                messages.info(request, "No changes detected.")

            return redirect("prospects:prospect_status", pk=prospect.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProspectStatusForm(instance=prospect)
        note_form = ProspectNoteQuickForm()

    name_for_title = (
        prospect.full_name
        or prospect.company_name
        or prospect.email
        or f"Prospect #{prospect.pk}"
    )
    title = f"Update Status — {name_for_title}"

    ctx = {
        "user_obj": request.user,
        "prospect": prospect,
        "form": form,
        "note_form": note_form,
    }
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/prospect_status.html", ctx)
