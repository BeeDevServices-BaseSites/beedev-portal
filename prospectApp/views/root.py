from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from core.utils.context import base_ctx
from ..forms import ProspectForm, ProspectEditForm, ProspectStatusForm, ProspectNoteQuickForm
from ..models import Prospect, ProspectNote
from companyApp.models import Company
from userApp.models import User
from django.urls import reverse
from django.db import transaction
from django.utils import timezone

def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER}

@login_required
def add_prospect(request):
    user = request.user
    # match your existing role-gate style
    allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER}
    if getattr(user, "role", None) not in allowed_roles:
        raise PermissionDenied("Not allowed")

    if request.method == "POST":
        form = ProspectForm(request.POST)
        if form.is_valid():
            prospect = form.save(commit=False)
            # if your model has these fields, they’ll set; otherwise remove
            if hasattr(prospect, "created_by"):
                prospect.created_by = user
            prospect.save()
            messages.success(request, "Prospect added successfully.")
            # send them somewhere useful; adjust as needed
            # if Prospect._meta.get_field("id"):
                # return redirect("prospectApp:detail", pk=prospect.pk)
            return redirect("userApp:view_all_clients")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProspectForm()

    title = "Add Prospect"
    ctx = {"form": form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/prospect_form.html", ctx)

@login_required
def view_prospect(request, pk: int):
    user = request.user
    allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER}
    if getattr(user, 'role', None) not in allowed_roles:
        raise PermissionDenied("Not allowed")
    
    prospect = get_object_or_404(Prospect, pk=pk)
    title = f"{prospect.full_name}'s Prospect File"
    ctx = {"user_obj": user, "prospect": prospect}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/view_one_prospect.html", ctx)

@login_required
def edit_prospect(request, pk: int):
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")

    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method == "POST":
        form = ProspectEditForm(request.POST, instance=prospect)
        if form.is_valid():
            obj = form.save(commit=False)
            if hasattr(obj, "contact_email") and obj.contact_email:
                obj.contact_email = obj.contact_email.strip().lower()
            obj.save()
            messages.success(request, "Prospect updated.")
            return redirect(reverse("prospects:prospect_edit", args=[prospect.pk]))
    else:
        form = ProspectEditForm(instance=prospect)

    name_for_title = getattr(prospect, "full_name", None) \
                     or getattr(prospect, "company_name", None) \
                     or getattr(prospect, "name", f"#{prospect.pk}")
    title = f"Edit Prospect — {name_for_title}"

    ctx = {"user_obj": request.user, "prospect": prospect, "form": form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/prospect_edit.html", ctx)

@login_required
def update_prospect_status(request, pk: int):
    if not _allowed_staff(request.user):
        raise PermissionDenied("Not allowed")

    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method == "POST":
        form = ProspectStatusForm(request.POST, instance=prospect)
        note_form = ProspectNoteQuickForm(request.POST)

        if form.is_valid() and note_form.is_valid():
            old_status = getattr(prospect, "status", None)

            # Save only changed fields to keep audits clean
            changed_fields = list(form.changed_data)
            prospect = form.save(commit=False)
            if changed_fields:
                try:
                    prospect.save(update_fields=changed_fields)
                except TypeError:
                    # update_fields=None would error; fall back to normal save
                    prospect.save()

            # Optionally append a running note entry if provided
            subj = (note_form.cleaned_data.get("subject") or "").strip()
            body = (note_form.cleaned_data.get("body_md") or "").strip()
            pinned = bool(note_form.cleaned_data.get("is_pinned"))
            if subj or body:
                ProspectNote.objects.create(
                    prospect=prospect,
                    subject=subj or "Note",
                    body_md=body,
                    is_pinned=pinned,
                    created_by=request.user if request.user.is_authenticated else None,
                )
                messages.success(request, "Note added to prospect history.")

            new_status = getattr(prospect, "status", None)

            if new_status == "WON":
                company = prospect.convert_to_company(actor=request.user)
                messages.success(
                    request,
                    f"Prospect marked WON and converted to Company: {company.name} "
                    f"(Contact: {company.primary_contact_name or '—'} <{company.primary_email or '—'}>)"
                )
                return redirect(reverse("company_staff:company_detail", args=[company.pk]))

            if changed_fields:
                messages.success(
                    request,
                    f"Status/fields updated ({', '.join(changed_fields)}) — "
                    f"status {old_status or '-'} → {new_status or '-'}"
                )
            else:
                messages.info(request, "No changes detected.")

            return redirect(reverse("prospects:prospect_status", args=[prospect.pk]))
    else:
        form = ProspectStatusForm(instance=prospect)
        note_form = ProspectNoteQuickForm()

    name_for_title = getattr(prospect, "full_name", None) \
                     or getattr(prospect, "company_name", None) \
                     or getattr(prospect, "name", f"#{prospect.pk}")
    title = f"Update Status — {name_for_title}"

    ctx = {"user_obj": request.user, "prospect": prospect, "form": form, "note_form": note_form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "prospectApp/prospect_status.html", ctx)