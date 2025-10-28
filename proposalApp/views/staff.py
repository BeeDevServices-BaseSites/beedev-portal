from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch, Max
from django.views.generic import TemplateView
from django.conf import settings
from importlib import import_module
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from ..models import ProposalDraft, DraftItem, DraftNote, Proposal, ProposalLineItem, ProposalAppliedDiscount, ProposalRecipient, ProposalEvent, CatalogItem, ProposalNote, ProposalSummary, ProposalViewer
from userApp.models import User
from companyApp.models import Company
from core.utils.context import base_ctx
from django.contrib import messages
from django.urls import reverse
from proposalApp.services.pdf_service import generate_proposal_pdf
from django.http import FileResponse, HttpResponseNotAllowed
from decimal import Decimal, InvalidOperation
from django.forms import formset_factory
from ..forms import NewDraftForm, DraftForm, DraftNoteForm, DraftNoteInlineFormSet, DraftItemInlineFormSet, AddViewerForm
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model

import logging
log = logging.getLogger(__name__)

def _is_owner(user):
    return user.is_active and (user.is_superuser or user.role == User.Roles.OWNER)

def _is_admin(user):
    return user.is_active and user.role == User.Roles.ADMIN

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_staff(user):
    return user.is_active and user.role in {
        User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER
    }

def _dec_or(default, raw):
    if raw is None or str(raw).strip() == "":
        return Decimal(str(default))
    try:
        d = Decimal(str(raw))
        if d < 0:
            return Decimal(str(default))
        return d
    except (InvalidOperation, ValueError):
        return Decimal(str(default))

try:
    import markdown
    def render_md(text: str):
        return mark_safe(markdown.markdown(
            text or "",
            extensions=["extra", "sane_lists", "tables", "fenced_code"]
        ))
except Exception:
    from django.utils.html import escape
    from django.template.defaultfilters import linebreaksbr
    def render_md(text: str):
        return mark_safe(linebreaksbr(escape(text or "")))

@login_required
def proposal_home(request):
    user = request.user
    if not _allowed_staff(request.user):
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

                for ci in catalog_qs:
                    if request.POST.get(f"item-{ci.id}-checked") == "on":
                        hours_raw = request.POST.get(f"item-{ci.id}-hours") or ci.default_hours
                        qty_raw   = request.POST.get(f"item-{ci.id}-qty")   or ci.default_quantity

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

                draft.recalc_totals(save=True)

            messages.success(request, "Draft created.")
            return redirect(reverse("proposal_staff:draft_detail", args=[draft.id]))

        title = "Create Draft"
        ctx = {"form": form, "notes_fs": notes_fs, "catalog_items": catalog_qs}
        ctx.update(base_ctx(request, title=title))
        ctx["page_heading"] = title
        return render(request, "proposal_staff/create_new_draft.html", ctx)

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
    if not _allowed_staff(user):
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
            ),
            Prefetch(
                "notes",
                queryset=DraftNote.objects.order_by("sort_order", "pk"),
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

        if action == "convert":
            if draft.approval_status != ProposalDraft.ApprovalStatus.APPROVED:
                messages.error(request, "Draft must be approved before conversion.")
                return redirect(request.path)
            with transaction.atomic():
                proposal = draft.convert_to_proposal(actor=user)
                base_url = request.build_absolute_uri("/")
                generate_proposal_pdf(
                    proposal,
                    request=request,
                    base_url=base_url,
                    overwrite=True,
                    delete_old=True,
                )
            messages.success(request, "Converted to proposal and generated PDF.")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.id]))

        messages.error(request, "Unknown action.")
        return redirect(request.path)

    theList = list(draft.items.all())

    summary_html = render_md(draft.summary_md or "")

    notes = [{
        "subject": (n.subject or "Notes"),
        "body_html": render_md(n.body_md or ""),
    } for n in draft.notes.all()]

    title = f"{draft.title} Proposal Draft"
    ctx = {"user_obj": user, "read_only": True, "draft": draft, "notes": notes, "items": theList, "summary_html": summary_html, "admin_users": admin_users, "can_approve": (user.role in (User.Roles.ADMIN, User.Roles.OWNER) or user.is_superuser)}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_staff/view_draft_detail.html", ctx)

@login_required
def edit_proposal_draft(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")
    
    draft = get_object_or_404(ProposalDraft.objects.select_related("company", "discount"), pk=pk)

    if getattr(ProposalDraft, "ApprovalStatus", None):
        if draft.approval_status == ProposalDraft.ApprovalStatus.CONVERTED:
            messages.error(request, "Converted drafts cannot be edited.")
            return redirect(reverse("proposal_staff:draft_detail", args=[draft.pk]))
        
    existing_items = {
        di.catalog_item_id: di
        for di in DraftItem.objects.select_related("catalog_item").filter(draft=draft)
    }

    catalog_qs = (
        CatalogItem.objects
        .select_related("job_rate", "base_setting")
        .filter(is_active=True)
        .order_by("sort_order", "name")
    )
    
    if request.method == "POST":
        form = DraftForm(request.POST, instance=draft)
        notes_fs = DraftNoteInlineFormSet(request.POST, instance=draft, prefix="notes", queryset=DraftNote.objects.order_by("sort_order", "pk"))

        if form.is_valid() and notes_fs.is_valid():
            with transaction.atomic():
                form.save()

                checked_ids = set()

                for ci in catalog_qs:
                    if request.POST.get(f"item-{ci.id}-checked") == "on":
                        checked_ids.add(ci.id)

                to_delete_ids = [cid for cid in existing_items.keys() if cid not in checked_ids]
                if to_delete_ids:
                    DraftItem.objects.filter(draft=draft, catalog_item_id__in=to_delete_ids).delete()
                    for cid in to_delete_ids:
                        existing_items.pop(cid, None)

                for ci in catalog_qs:
                    if ci.id not in checked_ids:
                        continue

                    hours_raw = (request.POST.get(f"items-{ci.id}-hours")
                                 or request.POST.get(f"item-{ci.id}-hours"))
                    qty_raw   = (request.POST.get(f"items-{ci.id}-qty")
                                 or request.POST.get(f"item-{ci.id}-qty"))


                    if ci.id in existing_items:
                        di = existing_items[ci.id]
                        di.hours    = _dec_or(di.hours,    hours_raw)
                        di.quantity = _dec_or(di.quantity, qty_raw)
                        if di.sort_order is None:
                            di.sort_order = 0
                        di.save()
                    else:
                        hours = _dec_or(ci.default_hours, hours_raw)
                        qty   = _dec_or(ci.default_quantity, qty_raw)
                        DraftItem.objects.create(
                            draft=draft,
                            catalog_item=ci,
                            hours=hours,
                            quantity=qty,
                        )

                note_objs = notes_fs.save(commit=False)
                for obj in note_objs:
                    if obj.sort_order is None:
                        obj.sort_order = 0
                    obj.save()
                for obj in notes_fs.deleted_objects:
                    obj.delete()

                for idx, it in enumerate(DraftItem.objects.filter(draft=draft).order_by("sort_order", "pk")):
                    if it.sort_order != idx:
                        it.sort_order = idx
                        it.save(update_fields=["sort_order"])

                for idx, nt in enumerate(DraftNote.objects.filter(draft=draft).order_by("sort_order", "pk")):
                    if nt.sort_order != idx:
                        nt.sort_order = idx
                        nt.save(update_fields=["sort_order"])
                
                if hasattr(draft, "recalc_totals"):
                    draft.recalc_totals(save=True)
            
            messages.success(request, "Draft updated.")
            return redirect(reverse("proposal_staff:draft_detail", args=[draft.pk]))
        else:
            log.info("FORM errors:", form.errors)
            log.info("NOTES non_form_errors:", notes_fs.non_form_errors())
            log.info("NOTES mgmt errors:", notes_fs.management_form.errors)
            for i, f in enumerate(notes_fs.forms):
                if f.errors:
                    log.info("NOTES form errors:", f.errors)
            messages.error(request, "Please fix the errors below.")

    else:
        form     = DraftForm(instance=draft)
        notes_fs = DraftNoteInlineFormSet(
            instance=draft,
            prefix="notes",
            queryset=DraftNote.objects.order_by("sort_order", "pk"),
        )
    
    catalog_items = []
    for ci in catalog_qs:
        ex = existing_items.get(ci.id)
        hourly = getattr(getattr(ci, "job_rate", None), "hourly_rate", Decimal("0"))
        base   = getattr(getattr(ci, "base_setting", None), "base_rate", Decimal("0"))
        catalog_items.append({
            "id": ci.id,
            "name": ci.name,
            "description": getattr(ci, "description", ""),
            "default_hours": ci.default_hours,
            "default_quantity": ci.default_quantity,
            "is_added": bool(ex),
            "hours": ex.hours if ex else ci.default_hours,
            "quantity": ex.quantity if ex else ci.default_quantity,
            "hourly": hourly,
            "base": base,
        })

    title = f"Edit Draft — {draft.title}"
    ctx = {
        "user_obj": user,
        "draft": draft,
        "form": form,
        "notes_fs": notes_fs,
        "catalog_items": catalog_items,
    }
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "proposal_staff/edit_draft.html", ctx)

@login_required
def view_proposal_detail(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
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
            ),
            Prefetch(
                "notes",
                queryset=ProposalNote.objects.filter(is_visible_to_client=True).order_by("sort_order", "pk"),
            ),
            Prefetch(
                "summary",
                queryset=ProposalSummary.objects.all()
            ),
            Prefetch(
                "allowed_viewers",
                queryset=ProposalViewer.objects.select_related("user")
            ),
        )
        .get(pk=pk)
    )
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "generate_sign_link":
            proposal.ensure_signing_link()
            messages.success(request, "Signing link generated.")
            return redirect(request.path)
        
        if action == "add_viewer":
            form = AddViewerForm(request.POST)
            if form.is_valid():
                client_user = form.cleaned_data["client"]
                ProposalViewer.objects.get_or_create(proposal=proposal, user=client_user)
                full_name = (client_user.get_full_name() or "").strip() or client_user.email or client_user.username
                messages.success(request, f"Added {full_name} as a viewer.")
                return redirect(request.path)
        elif action == "remove_viewer":
            pv_id = request.POST.get("pv_id")
            pv = get_object_or_404(ProposalViewer, pk=pv_id, proposal=proposal)
            u = pv.user
            display = (getattr(u, "get_full_name", lambda: "")() or u.email or u.username)
            pv.delete()
            messages.success(request, f"Removed {display} from viewers.")
            return redirect(request.path)
        else:
            form = AddViewerForm()
    else:
        form = AddViewerForm()

    assigned_clients = []
    for pv in proposal.allowed_viewers.select_related("user").all():
        u = pv.user
        name = (getattr(u, "get_full_name", lambda: "")() or "").strip()
        assigned_clients.append({
            "pv_id": pv.id,
            "name": name if name else (getattr(u, "email", None) or u.username),
            "email": getattr(u, "email", None),
            "id": u.id,
        })
        
    theList = list(proposal.line_items.all())
    events = list(proposal.events.all())
    summary_html = render_md(getattr(proposal.summary, "body_md", "") or "")

    notes_rendered = [
        {"subject": (n.subject or "Notes"), "body_html": render_md(n.body_md or "")}
        for n in proposal.notes.all()
    ]

    title = f"{proposal.title} Proposal"
    ctx = {"user_obj": user, "read_only": True, "proposal": proposal, "items": theList, "summary_html": summary_html, "events": events, "notes_rendered": notes_rendered, "assigned_clients": assigned_clients, "add_viewer_form": form,}
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

    base_url = request.build_absolute_uri("/")
    generate_proposal_pdf(proposal, request=request, base_url=base_url, overwrite=True,
    delete_old=True,)
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

    f = proposal.pdf.open("rb")
    resp = FileResponse(f, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{proposal.company.slug or "proposal"}-{proposal.pk}.pdf"'
    return resp

@login_required
def send_proposal(request, pk: int):
    user = request.user
    if not _allowed_staff(user):
        raise PermissionDenied("Not allowed")

    proposal = get_object_or_404(Proposal, pk=pk)

    if request.method == "POST":
        raw = (request.POST.get("emails") or "").strip()
        if not raw:
            messages.error(request, "Enter at least one recipient email.")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))
        
        pieces = [p.strip() for p in raw.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
        emails = []
        for e in pieces:
            try:
                validate_email(e)
                emails.append(e.lower())
            except ValidationError:
                pass

        emails = list(dict.fromkeys(emails))
        if not emails:
            messages.error(request, "No valid emails found.")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))

        created = 0
        made_primary = proposal.recipients.filter(is_primary=True).exists()
        for em in emails:
            obj, was_created = ProposalRecipient.objects.get_or_create(proposal=proposal, email=em, defaults={"is_primary": not made_primary})
            if was_created:
                created += 1
                if not made_primary:
                    made_primary = True

        hook_path = getattr(settings, "PROPOSAL_MESSENGER", "")
        try:
            proposal.ensure_signing_link()
            if hook_path:
                mod_path, fn_name = hook_path.split(":") if ":" in hook_path else hook_path.rsplit(".", 1)
                mod = __import__(mod_path, fromlist=[fn_name])
                hook = getattr(mod, fn_name)
                hook(proposal, emails, proposal.get_signing_url(), attach_pdf=bool(proposal.pdf), sender_user=request.user,)
            else:
                raise RuntimeError("PROPOSAL_MESSENGER not configured")
        
        except Exception as e:
            messages.error(request, f"Email send failed: {e!r}")
            return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))

        proposal.mark_sent(actor=user, skip_messenger=True)

        messages.success(request, f"Sent to {len(emails)} recipient(s). (Added {created} new)")
        return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))

    return redirect(reverse("proposal_staff:proposal_detail", args=[proposal.pk]))