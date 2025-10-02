from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch, Max
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from ..models import ProposalDraft, DraftItem, DraftNote, Proposal, ProposalLineItem, ProposalAppliedDiscount, ProposalRecipient, ProposalEvent, CatalogItem
from userApp.models import User
from companyApp.models import Company
from core.utils.context import base_ctx
from django.contrib import messages
from django.urls import reverse
from proposalApp.pdf import generate_proposal_pdf
from django.http import FileResponse, HttpResponseNotAllowed
from decimal import Decimal
from django.forms import formset_factory
from ..forms import NewDraftForm, DraftNoteForm

def _is_owner(user):
    return user.is_active and (user.is_superuser or user.role == User.Roles.OWNER)

def _is_admin(user):
    return user.is_active and user.role == User.Roles.ADMIN

def _is_employee(user):
    return user.is_active and (user.role in [User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER])

def _allowed_staff(user):
    return user.is_active and user.role in {
        User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER
    }

@login_required
def proposal_home(request):
    user = request.user
    allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER}
    if getattr(user, "role", None) not in allowed_roles:
        raise PermissionDenied("Not allowed")
    drafts = ProposalDraft.objects.exclude(approval_status='CONVERTED')

    proposals_qs = (
        Proposal.objects
        .select_related("company")
        .annotate(last_event_at=Max("events__at"))
        .prefetch_related(
            Prefetch(
                "events",
                queryset=ProposalEvent.objects.select_related("actor").order_by("-at", "pk")
            )
        )
        .order_by("-last_event_at", "-created_at")
    )
    proposals = list(proposals_qs)
    last_events_by_id = {
        p.id: (p.events.all()[0] if p.events.all() else None)
        for p in proposals
    }
    title = "Proposal Admin"
    ctx = {"user_obj": user, "read_only": True, "drafts": drafts, "proposals": proposals, "last_events_by_id": last_events_by_id}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_staff/proposal_home.html", ctx)

@login_required
def create_new_draft(request):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    NoteFormSet = formset_factory(DraftNoteForm, extra=2, can_delete=True)

    catalog_qs = (
        CatalogItem.objects
        .select_related("job_rate", "base_setting")
        .filter(is_active=True)
        .order_by("sort_order", "name")
    )

    if request.method == "POST":
        form = NewDraftForm(request.POST)
        notes_fs = NoteFormSet(request.POST, prefix="notes")

        if form.is_valid() and notes_fs.is_valid():
            company  = form.cleaned_data["company"]
            title    = form.cleaned_data["title"].strip()
            currency = form.cleaned_data["currency"].strip()
            discount = form.cleaned_data.get("discount")

            # Auto-fill (and normalize) contact if left blank
            contact_name  = (form.cleaned_data.get("contact_name")  or company.primary_contact_name or "").strip()
            contact_email = (form.cleaned_data.get("contact_email") or company.primary_email        or "").strip().lower()

            with transaction.atomic():
                draft = ProposalDraft.objects.create(
                    company=company,
                    created_by=user,
                    title=title,
                    currency=currency,
                    discount=discount,
                    contact_name=contact_name,
                    contact_email=contact_email,
                )

                # Selected catalog items -> DraftItem rows
                for ci in catalog_qs:
                    if request.POST.get(f"item-{ci.id}-checked") == "on":
                        hours_raw = request.POST.get(f"item-{ci.id}-hours") or ci.default_hours
                        qty_raw   = request.POST.get(f"item-{ci.id}-qty")   or ci.default_quantity

                        # sanitize
                        try:
                            hours = Decimal(str(hours_raw))
                            if hours < 0: hours = ci.default_hours
                        except Exception:
                            hours = ci.default_hours
                        try:
                            qty = Decimal(str(qty_raw))
                            if qty < 0: qty = ci.default_quantity
                        except Exception:
                            qty = ci.default_quantity

                        DraftItem.objects.create(
                            draft=draft,
                            catalog_item=ci,
                            hours=hours,
                            quantity=qty,
                        )

                # Notes formset
                sort = 0
                for nf in notes_fs:
                    if notes_fs.can_delete and nf.cleaned_data.get("DELETE"):
                        continue
                    subj = (nf.cleaned_data.get("subject") or "").strip()
                    body = (nf.cleaned_data.get("body_md") or "").strip()
                    if subj or body:
                        DraftNote.objects.create(
                            draft=draft,
                            sort_order=sort,
                            subject=subj or "Notes",
                            body_md=body,
                        )
                        sort += 1

                # Optional: if you removed recalc from DraftItem.save(), keep this.
                # Otherwise it's safe to omit (avoids double work).
                draft.recalc_totals(save=True)

            messages.success(request, "Draft created.")
            return redirect(reverse("proposal_staff:draft_detail", args=[draft.id]))

        # invalid -> re-render
        title = "Create Draft"
        ctx = {"form": form, "notes_fs": notes_fs, "catalog_items": catalog_qs}
        ctx.update(base_ctx(request, title=title))
        ctx["page_heading"] = title
        return render(request, "proposal_staff/create_new_draft.html", ctx)

    # GET
    form = NewDraftForm()
    notes_fs = NoteFormSet(prefix="notes")
    title = "Create Draft"
    ctx = {"form": form, "notes_fs": notes_fs, "catalog_items": catalog_qs}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_staff/create_new_draft.html", ctx)


@login_required
def view_draft_detail(request, pk: int):
    user = request.user
    allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER}
    if getattr(user, "role", None) not in allowed_roles:
        raise PermissionDenied("Not allowed")
    
    draft = (
        ProposalDraft.objects
        .select_related("company", "discount", "estimate_tier")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=DraftItem.objects
                    .select_related("job_rate", "base_setting", "catalog_item")
                    .order_by("sort_order", "pk"),
            )
        )
        .filter(pk=pk)
        .first()
    )
    if not draft:
        raise PermissionDenied("Draft not found")
    
    admin_users = User.objects.filter(is_active=True, role__in=[User.Roles.ADMIN, User.Roles.OWNER]).order_by("first_name", "last_name", "username")

    if request.method == "POST":
        action = request.POST.get("action")

        # 1) Submit for approval
        if action == "submit":
            reviewer_id = request.POST.get("reviewer_id")
            if reviewer_id and hasattr(draft, "assigned_reviewer_id"):
                try:
                    draft.assigned_reviewer_id = int(reviewer_id)
                    draft.save(update_fields=["assigned_reviewer_id"])
                except Exception:
                    pass
            
            try:
                draft.mark_submitted(actor=user, save=True)
            except ValidationError as e:
                messages.error(
                    request, "Cannot submit: the company is missing a primary email."
                    "Add it to the Company and try again."
                )
                return redirect(request.path)
            messages.success(request, "Draft submitted for approval.")
            return redirect(request.path)

        # 2) Approve / Reject (Admin/Owner only)
        if action in {"approve", "reject"}:
            if not (user.role in (User.Roles.ADMIN, User.Roles.OWNER) or user.is_superuser):
                raise PermissionDenied("Only Admin/Owner may approve or reject drafts.")
            notes = (request.POST.get("approval_notes") or "").strip()
            if action == "approve":
                draft.mark_approved(actor=user, notes=notes, save=True)
                messages.success(request, "Draft approved.")
            else:
                draft.mark_rejected(actor=user, notes=notes, save=True)
                messages.info(request, "Draft rejected.")
            return redirect(request.path)

        # 3) Convert to Proposal (only after Approved)
        if action == "convert":
            if draft.approval_status != ProposalDraft.ApprovalStatus.APPROVED:
                messages.error(request, "Draft must be approved before conversion.")
                return redirect(request.path)
            with transaction.atomic():
                proposal = draft.convert_to_proposal(actor=user)
                base_url = request.build_absolute_uri("/")
                # This controls replacing the pdf... (this will keep one version per proposal)
                generate_proposal_pdf(proposal, base_url=base_url, force=True, overwrite=True, delete_old=True)
                # This controls versioning the pdf... (this will keep multiple versions per proposal)
                # generate_proposal_pdf(proposal, base_url=base_url, overwrite=False)
            messages.success(request, "Converted to proposal and generated PDF.")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.id]))

        messages.error(request, "Unknown action.")
        return redirect(request.path)

    
    theList = list(draft.items.all())
    title = f"{draft.title} Proposal Draft"
    ctx = {"user_obj": user, "read_only": True, "draft": draft, "items": theList, "admin_users": admin_users, "can_approve": (user.role in (User.Roles.ADMIN, User.Roles.OWNER) or user.is_superuser)}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_staff/view_draft_detail.html", ctx)

@login_required
def view_proposal_detail(request, pk: int):
    user = request.user
    allowed_roles = {user.Roles.EMPLOYEE, user.Roles.ADMIN, user.Roles.OWNER}
    if getattr(user, "role", None) not in allowed_roles:
        raise PermissionDenied("Not allowed")
    
    proposal = (
        Proposal.objects
        .select_related("company", "created_by", "approver_user")
        .prefetch_related(
            Prefetch(
                "line_items",
                queryset=ProposalLineItem.objects
                    .select_related("job_rate", "base_setting")
                    .order_by("sort_order", "pk"),
            ),
            Prefetch(
                "applied_discounts",
                queryset=ProposalAppliedDiscount.objects.order_by("sort_order", "id")
            ),
            Prefetch(
                "recipients",
                queryset=ProposalRecipient.objects.order_by("-is_primary", "email")
            ),
            Prefetch(
                "events",
                queryset=ProposalEvent.objects.select_related("actor").order_by("-at", "pk")
            )
        )
        .get(pk=pk)
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate_sign_link":
            proposal.ensure_signing_link()
            messages.success(request, "Signing link generated.")
            return redirect(request.path)
        
    theList = list(proposal.line_items.all())
    events = list(proposal.events.all())

    title = f"{proposal.title} Proposal"
    ctx = {"user_obj": user, "read_only": True, "proposal": proposal, "items": theList, "events": events}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title 
    return render(request, "proposal_staff/view_proposal_detail.html", ctx)

@login_required
def generate_proposal_pdf_view(request, pk: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    proposal = get_object_or_404(Proposal.objects.select_related("company"), pk=pk)

    # Render/overwrite PDF (clean dev behavior)
    base_url = request.build_absolute_uri("/")
    generate_proposal_pdf(proposal, request=request, base_url=base_url, force=True)
    messages.success(request, "PDF generated.")
    return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.id]))

@login_required
def view_proposal_pdf(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    proposal = get_object_or_404(Proposal.objects.select_related("company"), pk=pk)

    if not proposal.pdf:
        messages.info(request, "No PDF has been generated yet.")
        return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.id]))

    # Stream the PDF inline
    f = proposal.pdf.open("rb")
    resp = FileResponse(f, content_type="application/pdf")
    # Show in-browser (inline) with a readable filename
    resp["Content-Disposition"] = f'inline; filename="{proposal.company.slug or "proposal"}-{proposal.pk}.pdf"'
    return resp

@login_required
def send_proposal(request, pk: int):
    user = request.user
    if not (user.is_active and (user.is_superuser or user.role in [User.Roles.ADMIN, User.Roles.OWNER, User.Roles.EMPLOYEE])):
        raise PermissionDenied("Not allowed")

    proposal = get_object_or_404(Proposal, pk=pk)

    if request.method == "POST":
        raw = (request.POST.get("emails") or "").strip()
        if not raw:
            messages.error(request, "Enter at least one recipient email.")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))

        emails = {e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()}
        if not emails:
            messages.error(request, "No valid emails found.")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))

        # Upsert recipients
        created = 0
        for em in emails:
            obj, was_created = ProposalRecipient.objects.get_or_create(proposal=proposal, email=em, defaults={"is_primary": True})
            if was_created:
                created += 1

        # This will generate/refresh the token + fire your messenger hook
        proposal.mark_sent(actor=user)

        messages.success(request, f"Queued send to {len(emails)} recipient(s). (Added {created} new)")
        return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))

    return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))