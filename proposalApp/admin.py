# proposalApp/admin.py
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse, NoReverseMatch
from urllib.parse import urljoin
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import proposal_pdf_upload_to
from proposalApp.services import pdf_stamp
from companyApp.models import CompanyMembership
from userApp.models import User
from .models import (
    JobRate,
    BaseSetting,
    Discount,
    CatalogItem,
    ProposalDraft,
    DraftItem,
    DraftNote,
    Proposal,
    ProposalLineItem,
    ProposalAppliedDiscount,
    ProposalRecipient,
    ProposalEvent,
    CostTier,
    ProposalViewer,
    ProposalSection,
    ProposalNote,
    ProposalSummary,
)

try:
    from django.contrib.sites.models import Site
except Exception:
    Site = None

# =========================
# Permission helpers
# =========================

def is_owner(u):
    return u.is_active and (u.is_superuser or u.groups.filter(name="Owner").exists())

def is_admin(u):
    return u.is_active and u.groups.filter(name="Admin").exists()

def is_hr(u):
    return u.is_active and u.groups.filter(name="HR").exists()

def is_plain_staff(u):
    return u.is_active and u.is_staff and not is_owner(u) and not is_admin(u) and not is_hr(u)


# =========================
# Money & totals helpers
# =========================

def q2(val):
    """Quantize to cents with HALF_UP rounding."""
    if val is None:
        val = Decimal("0")
    return Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _recompute_proposal_totals(p: Proposal):
    discounts_sum = p.applied_discounts.aggregate(s=Sum("amount_applied"))["s"] or Decimal("0.00")
    p.discount_total = q2(discounts_sum)
    p.amount_total = q2((p.amount_subtotal or 0) - p.discount_total)

    p.amount_total = q2((p.amount_subtotal or 0) - p.discount_total)
    if p.amount_total < Decimal("0.00"):
        p.amount_total = Decimal("0.00")

    if p.deposit_type == ProposalDraft.DepositType.PERCENT:
        dep = q2((p.amount_subtotal or 0) * (p.deposit_value or 0) / Decimal("100"))
    elif p.deposit_type == ProposalDraft.DepositType.FIXED:
        dep = q2(p.deposit_value or 0)
    else:
        dep = Decimal("0.00")

    # Cap deposit to post-discount total
    if p.amount_total <= Decimal("0.00"):
        dep = Decimal("0.00")
    elif dep > p.amount_total:
        dep = p.amount_total

    p.deposit_amount = dep
    p.remaining_due = q2(p.amount_total - dep)
    p.save(update_fields=["discount_total", "amount_total", "deposit_amount", "remaining_due", "updated_at"])


# =========================
# Reference/Admin catalogs
# =========================

@admin.register(JobRate)
class JobRateAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "hourly_rate", "is_active", "sort_order")
    list_filter  = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")

    def has_view_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)
    def has_add_permission(self, request): return is_owner(request.user) or is_admin(request.user)
    def has_change_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)
    def has_delete_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)

@admin.register(BaseSetting)
class BaseSettingAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "base_rate", "is_active", "sort_order")
    list_filter  = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")

    def has_view_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)
    def has_add_permission(self, request): return is_owner(request.user) or is_admin(request.user)
    def has_change_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)
    def has_delete_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "value", "is_active")
    list_filter  = ("is_active", "kind")
    search_fields = ("name", "code")
    ordering = ("code",)

    def has_module_permission(self, request):
        if is_hr(request.user) or not request.user.is_staff:
            return False
        return True
    def has_view_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_add_permission(self, request): return is_owner(request.user) or is_admin(request.user)
    def has_change_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)
    def has_delete_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)

@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display  = ("name", "code", "job_rate", "base_setting", "default_hours", "default_quantity", "is_active", "sort_order")
    list_filter   = ("is_active", "job_rate", "base_setting")
    search_fields = ("name", "code", "tags")
    ordering      = ("sort_order", "name")
    autocomplete_fields = ("job_rate", "base_setting")

    def has_module_permission(self, request):
        if is_hr(request.user) or not request.user.is_staff:
            return False
        return True
    def has_view_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_add_permission(self, request): return is_owner(request.user) or is_admin(request.user)
    def has_change_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)
    def has_delete_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)

@admin.register(CostTier)
class CostTierAdmin(admin.ModelAdmin):
    list_display  = ("label", "code", "min_total", "max_total", "is_active", "sort_order")
    list_filter   = ("is_active",)
    search_fields = ("label", "code", "notes")
    ordering      = ("sort_order", "min_total")

    def has_module_permission(self, request):
        if is_hr(request.user) or not request.user.is_staff:
            return False
        return True
    def has_view_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_add_permission(self, request): return is_owner(request.user) or is_admin(request.user)
    def has_change_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)
    def has_delete_permission(self, request, obj=None): return is_owner(request.user) or is_admin(request.user)

# =========================
# DRAFTS
# =========================

@admin.action(description="Mark discount verified (Draft)")
def mark_draft_discount_verified(modeladmin, request, queryset):
    now = timezone.now()
    for d in queryset:
        d.is_discount_verified = True
        d.verification_checked_at = now
        d.verification_checked_by = request.user
        d.recalc_totals(save=True)

@admin.action(description="Revoke discount verification (Draft)")
def revoke_draft_discount_verified(modeladmin, request, queryset):
    now = timezone.now()
    for d in queryset:
        d.is_discount_verified = False
        d.verification_checked_at = now
        d.verification_checked_by = request.user
        d.recalc_totals(save=True)

class DraftItemInline(admin.TabularInline):
    model = DraftItem
    extra = 0
    fields = (
        "sort_order",
        "catalog_item",
        "name", "description", "job_rate", "base_setting",
        "hours", "quantity",
        "line_hours_display",
        "line_total",
    )
    readonly_fields = ("name", "description", "job_rate", "base_setting", "line_hours_display", "line_total")
    autocomplete_fields = ("catalog_item",)

    def line_hours_display(self, obj):
        if not obj.pk:
            return "-"
        return (obj.hours or 0) * (obj.quantity or 0)
    line_hours_display.short_description = "Line Hours"

class DraftNoteInline(admin.TabularInline):
    model = DraftNote
    extra = 0
    fields = ("sort_order", "subject", "body_md")
    ordering = ("sort_order", "id")

@admin.action(description="Pre-sign (Owner/Admin only)")
def action_pre_sign(self, request, queryset):
    if not (is_owner(request.user) or is_admin(request.user)):
        self.message_user(request, "You do not have permission to pre-sign.", level=messages.ERROR)
        return
    n = 0
    for d in queryset:
        # optional: require APPROVED status first
        if d.approval_status not in (ProposalDraft.ApprovalStatus.APPROVED,):
            continue
        d.mark_pre_signed(actor=request.user, payload={"name": request.user.get_full_name() or str(request.user)})
        n += 1
    self.message_user(request, f"Pre-signed {n} draft(s).", level=messages.SUCCESS)

@admin.action(description="Revoke pre-sign")
def action_revoke_pre_sign(self, request, queryset):
    n = 0
    for d in queryset:
        if d.is_pre_signed:
            d.revoke_pre_sign(actor=request.user, reason="Admin revoke")
            n += 1
    self.message_user(request, f"Revoked pre-sign on {n} draft(s).", level=messages.SUCCESS)

@admin.register(ProposalDraft)
class ProposalDraftAdmin(admin.ModelAdmin):
    inlines = [DraftItemInline, DraftNoteInline]

    list_display = (
        "title", "company", "currency", "total_hours",
        "subtotal", "discount", "discount_amount",
        "total",
        "estimate_tier", "estimate_low", "estimate_high",
        "estimate_manual",
        "deposit_type", "deposit_value", "deposit_amount",
        "is_discount_verified", "discount_requires_verification",
        "remaining_due",
        "approval_status", "approved_by", "approved_at",
        "created_at", "is_pre_signed"
    )
    list_filter = ("discount_requires_verification", "is_discount_verified", "company", "deposit_type", "approval_status", "created_at")
    search_fields = ("title", "company__name", "contact_name", "contact_email")
    ordering = ("-created_at",)

    fieldsets = (
        ("Header", {"fields": ("company", "created_by", "title", "currency")}),
        ("Optional Contact", {"fields": ("contact_name", "contact_email"), "classes": ("collapse",)}),
        ("Discount", {"fields": ("discount", "discount_amount")}),
        ("Totals & Deposit", {
            "fields": (
                ("total_hours",),
                ("subtotal", "total"),
                ("deposit_type", "deposit_value", "deposit_amount"),
                "remaining_due",
            )
        }),
        ("Estimated Tier", {
            "fields": (
                "estimate_manual",
                "estimate_tier",
                ("estimate_low", "estimate_high"),
            ),
        }),
        ("Approval", {
            "fields": (
                "approval_status",
                ("submitted_at", "approved_at", "approved_by"),
                "approval_notes",
            ),
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = (
        "total_hours",
        "subtotal", "discount_amount", "total",
        "deposit_amount", "remaining_due",
        "estimate_low", "estimate_high",
        "created_at", "updated_at",
        "submitted_at", "approved_at", "approved_by",
        "pre_signed_at","pre_signed_by","pre_signature_hash"
    )

    actions = [
        # draft-specific actions
        mark_draft_discount_verified,
        revoke_draft_discount_verified,
        # utility actions
        "action_recalc_totals",
        "action_submit_for_approval",
        "action_approve_drafts",
        "action_reject_drafts",
        "action_convert_to_proposal",
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.recalc_totals(save=True)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalc_totals(save=True)

    @admin.action(description="Recalculate totals")
    def action_recalc_totals(self, request, queryset):
        for draft in queryset:
            draft.recalc_totals(save=True)
        self.message_user(request, f"Recalculated totals for {queryset.count()} draft(s).", level=messages.SUCCESS)

    @admin.action(description="Submit for approval")
    def action_submit_for_approval(self, request, queryset):
        count = 0
        for d in queryset:
            if getattr(d, "approval_status", None) in (getattr(ProposalDraft.ApprovalStatus, "DRAFT", "DRAFT"),
                                                       getattr(ProposalDraft.ApprovalStatus, "REJECTED", "REJECTED")):
                d.mark_submitted(actor=request.user, save=True)
                count += 1
        self.message_user(request, f"Submitted {count} draft(s) for approval.", level=messages.SUCCESS)

    @admin.action(description="Approve selected (Owner/Admin only)")
    def action_approve_drafts(self, request, queryset):
        if not (is_owner(request.user) or is_admin(request.user)):
            self.message_user(request, "You do not have permission to approve drafts.", level=messages.ERROR)
            return
        count = 0
        for d in queryset:
            if getattr(d, "approval_status", None) in (getattr(ProposalDraft.ApprovalStatus, "SUBMITTED", "SUBMITTED"),
                                                       getattr(ProposalDraft.ApprovalStatus, "DRAFT", "DRAFT")):
                d.mark_approved(actor=request.user, save=True)
                count += 1
        self.message_user(request, f"Approved {count} draft(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected (Owner/Admin only)")
    def action_reject_drafts(self, request, queryset):
        if not (is_owner(request.user) or is_admin(request.user)):
            self.message_user(request, "You do not have permission to reject drafts.", level=messages.ERROR)
            return
        count = 0
        for d in queryset:
            if getattr(d, "approval_status", None) in (
                getattr(ProposalDraft.ApprovalStatus, "SUBMITTED", "SUBMITTED"),
                getattr(ProposalDraft.ApprovalStatus, "DRAFT", "DRAFT"),
                getattr(ProposalDraft.ApprovalStatus, "APPROVED", "APPROVED"),
            ):
                d.mark_rejected(actor=request.user, save=True)
                count += 1
        self.message_user(request, f"Rejected {count} draft(s).", level=messages.SUCCESS)

    @admin.action(description="Convert to Proposal")
    @transaction.atomic
    def action_convert_to_proposal(self, request, queryset):
        not_ok = queryset.exclude(approval_status=getattr(ProposalDraft.ApprovalStatus, "APPROVED", "APPROVED")).count()
        if not_ok:
            self.message_user(
                request,
                "Conversion blocked: All selected drafts must be APPROVED.",
                level=messages.ERROR,
            )
            return
        created = 0
        for draft in queryset:
            draft.recalc_totals(save=True)
            proposal = draft.convert_to_proposal(actor=request.user)
            try:
                if proposal and getattr(draft, "approved_by_id", None) and not getattr(proposal, "approver_user_id", None):
                    proposal.approver_user_id = draft.approved_by_id
                    proposal.save(update_fields=["approver_user"])
            except Exception:
                pass
            created += 1
        self.message_user(request, f"Created {created} proposal(s) from selected draft(s).", level=messages.SUCCESS)

# =========================
# PROPOSALS
# =========================

class ProposalRecipientInline(admin.TabularInline):
    model = ProposalRecipient
    extra = 0
    fields = ("is_primary", "name", "email", "delivered_at", "last_opened_at")

class ProposalEventInline(admin.TabularInline):
    model = ProposalEvent
    extra = 0
    can_delete = False
    readonly_fields = ("kind", "at", "actor", "ip_address", "data")
    fields = ("kind", "at", "actor", "ip_address", "data")
    show_change_link = False

class ProposalLineItemInline(admin.TabularInline):
    model = ProposalLineItem
    extra = 0
    readonly_fields = ("line_total", "unit_price", "subtotal", "line_hours")
    fields = (
        "sort_order", "name", "description",
        "hours", "quantity", "job_rate", "base_setting", "line_hours",
        "line_total", "unit_price", "subtotal",
    )

class ProposalAppliedDiscountInline(admin.TabularInline):
    model = ProposalAppliedDiscount
    extra = 0
    fields = ("discount_code", "name", "kind", "value", "amount_applied", "sort_order")
    can_delete = False

class ProposalViewerInline(admin.TabularInline):
    model = ProposalViewer
    extra = 0
    autocomplete_fields = ("user",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "user":
            prop = getattr(request, "_current_proposal_obj", None)
            if prop and prop.pk:
                member_user_ids = CompanyMembership.objects.filter(
                    company=prop.company, is_active=True
                ).values_list("user_id", flat=True)
                field.queryset = field.queryset.filter(pk__in=member_user_ids)
        return field

class ProposalSectionInline(admin.TabularInline):
    model = ProposalSection
    extra = 0
    # If your model doesn't have `is_client_visible`, remove it from fields:
    fields = ("sort_order", "subject", "body_md", "is_client_visible")
    ordering = ("sort_order", "id")

@admin.register(ProposalSummary)
class ProposalSummaryAdmin(admin.ModelAdmin):
    list_display = ("proposal", "is_visible_to_client", "updated_at")
    list_filter = ("is_visible_to_client",)

@admin.register(ProposalNote)
class ProposalNoteAdmin(admin.ModelAdmin):
    list_display = ("proposal", "subject", "sort_order", "is_visible_to_client")
    list_filter = ("is_visible_to_client",)
    search_fields = ("subject", "body_md")
    ordering = ("proposal", "sort_order", "pk")

# ----- Proposal actions (module scope) -----
@admin.action(description="Backfill company countersign (append certificate)")
def action_backfill_countersign(self, request, queryset):
    user = request.user
    n_ok, n_err = 0, 0
    for p in queryset:
        try:
            # Set countersign metadata if missing
            if not p.countersigned_at:
                p.countersigned_at = timezone.now()
                p.countersigned_by = user
                p.countersign_required = False
                p.save(update_fields=["countersigned_at","countersigned_by","countersign_required","updated_at"])

            fname, data = pdf_stamp.append_certificate(p, user)  # or overlay_signature_on_last_page(p, user)
            # Save as new file (don’t overwrite original path)
            storage_name = proposal_pdf_upload_to(p, fname)
            default_storage.save(storage_name, ContentFile(data))
            p.pdf.name = storage_name
            p.save(update_fields=["pdf", "updated_at"])
            n_ok += 1
        except Exception as e:
            n_err += 1
    self.message_user(request, f"Countersigned {n_ok} PDF(s). Errors: {n_err}.")

@admin.action(description="Mark discount verified (Proposal)")
def mark_proposal_discount_verified(modeladmin, request, queryset):
    now = timezone.now()
    for p in queryset:
        # If verification fields exist on Proposal, update them:
        if hasattr(p, "is_discount_verified"):
            p.is_discount_verified = True
            if hasattr(p, "verification_checked_at"):
                p.verification_checked_at = now
            if hasattr(p, "verification_checked_by"):
                p.verification_checked_by = request.user
            p.save(update_fields=[
                *(["is_discount_verified"] if hasattr(p, "is_discount_verified") else []),
                *(["verification_checked_at"] if hasattr(p, "verification_checked_at") else []),
                *(["verification_checked_by"] if hasattr(p, "verification_checked_by") else []),
            ])

        # Flip pending verification-required discounts to active
        for ad in p.applied_discounts.all():
            requires_ver = getattr(ad, "requires_verification", False)
            pending = getattr(ad, "pending_verification", False)
            if requires_ver and pending:
                if ad.kind == "PERCENT":
                    ad.amount_applied = q2((p.amount_subtotal or 0) * (ad.value or 0) / Decimal("100"))
                else:
                    ad.amount_applied = q2(ad.value or 0)
                if hasattr(ad, "pending_verification"):
                    ad.pending_verification = False
                ad.save(update_fields=["amount_applied", *(["pending_verification"] if hasattr(ad, "pending_verification") else [])])

        _recompute_proposal_totals(p)

@admin.action(description="Revoke discount verification (Proposal)")
def revoke_proposal_discount_verified(modeladmin, request, queryset):
    now = timezone.now()
    for p in queryset:
        if hasattr(p, "is_discount_verified"):
            p.is_discount_verified = False
            if hasattr(p, "verification_checked_at"):
                p.verification_checked_at = now
            if hasattr(p, "verification_checked_by"):
                p.verification_checked_by = request.user
            p.save(update_fields=[
                *(["is_discount_verified"] if hasattr(p, "is_discount_verified") else []),
                *(["verification_checked_at"] if hasattr(p, "verification_checked_at") else []),
                *(["verification_checked_by"] if hasattr(p, "verification_checked_by") else []),
            ])

        for ad in p.applied_discounts.all():
            requires_ver = getattr(ad, "requires_verification", False)
            if requires_ver:
                ad.amount_applied = Decimal("0.00")
                if hasattr(ad, "pending_verification"):
                    ad.pending_verification = True
                    ad.save(update_fields=["amount_applied", "pending_verification"])
                else:
                    ad.save(update_fields=["amount_applied"])

        _recompute_proposal_totals(p)

def _public_base_url() -> str:
    base = getattr(settings, "PROPOSAL_PUBLIC_BASE_URL", None)
    if base:
        return base.rstrip("/")

    if Site is not None:
        try:
            current = Site.objects.get_current()
            if getattr(current, "domain", None):
                scheme = getattr(settings, "DEFAULT_HTTP_SCHEME", "https")
                return f"{scheme}://{current.domain}".rstrip("/")
        except Exception:
            pass

    return "http://127.0.0.1:8000"

def _abs_url(url_or_path: str | None) -> str | None:
    if not url_or_path:
        return None
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return url_or_path
    base = _public_base_url()
    return urljoin(base + "/", url_or_path.lstrip("/"))

def _account_signup_link(email: str | None) -> str | None:
    base = getattr(settings, "PROPOSAL_ACCOUNT_SIGNUP_URL", None)
    if not base:
        try:
            base = reverse("account_signup")
        except NoReverseMatch:
            base = None
    if not base:
        return None

    base_abs = _abs_url(base)
    if email:
        sep = "&" if "?" in base_abs else "?"
        return f"{base_abs}{sep}email={email}"
    return base_abs

def _send_links_email(proposal, *, to_email: str, include_pdf: bool, include_signup: bool) -> bool:
    pdf_url = _abs_url(getattr(getattr(proposal, "pdf", None), "url", None)) if include_pdf else None
    signup_url = _account_signup_link(getattr(proposal, "contact_email", None)) if include_signup else None

    if not (pdf_url or signup_url):
        return False

    subject = f"Proposal Links: {proposal.title} — {proposal.company.name}"

    greet = (f"Hi {proposal.contact_name}".strip() if proposal.contact_name else "Hello,")
    lines = [greet, "", "Here are your proposal links:"]
    if pdf_url:
        lines.append(f"- Signed PDF: {pdf_url}")
    if signup_url:
        lines.append(f"- Create your account: {signup_url}")
    lines += ["", "If you have any questions, just reply to this email.", "", "— BeeDev Services"]
    body_txt = "\n".join(lines)

    html_parts = [f"<p>{greet}</p>", "<p>Here are your proposal links:</p>", "<ul>"]
    if pdf_url:
        html_parts.append(f'<li>Signed PDF: <a href="{pdf_url}" target="_blank" rel="noopener">{pdf_url}</a></li>')
    if signup_url:
        html_parts.append(f'<li>Create your account: <a href="{signup_url}" target="_blank" rel="noopener">{signup_url}</a></li>')
    html_parts.append("</ul><p>If you have any questions, just reply to this email.</p><p>— BeeDev Services</p>")
    body_html = "".join(html_parts)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_txt,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
        cc=(getattr(settings, "PROPOSAL_CC", "") or "").split(",") if getattr(settings, "PROPOSAL_CC", "") else [],
        bcc=(getattr(settings, "PROPOSAL_BCC", "") or "").split(",") if getattr(settings, "PROPOSAL_BCC", "") else [],
        reply_to=[getattr(settings, "PROPOSAL_REPLY_TO", "")] if getattr(settings, "PROPOSAL_REPLY_TO", "") else None,
    )
    msg.attach_alternative(body_html, "text/html")
    try:
        msg.send(fail_silently=False)
        return True
    except Exception:
        return False

@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    inlines = [
        ProposalRecipientInline,
        ProposalEventInline,
        ProposalLineItemInline,
        ProposalAppliedDiscountInline,
        ProposalViewerInline,
        ProposalSectionInline,
    ]

    list_display = (
        "title", "company", "contact_email", "currency", "hours_subtotal", "hours_total",
        "amount_subtotal", "discount_total", "amount_tax", "amount_total",
        "deposit_type", "deposit_value", "deposit_amount",
        "remaining_due", "sent_at", "signed_at",
        "countersign_flag",
        "sign_link_short",
        "pdf_link",
        "created_at",
    )
    list_filter = ("company", "deposit_type", "countersign_required", "created_at")
    search_fields = ("title", "company__name")
    ordering = ("-created_at",)

    readonly_fields = (
        "hours_subtotal", "hours_total", "created_at", "updated_at",
        "sent_at", "viewed_at", "signed_at",
        "sign_token", "token_expires_at",
        "sign_link_preview",
        "countersigned_at", "countersigned_by",
    )

    fieldsets = (
        ("Header", {"fields": ("company", "created_by", "title", "currency")}),
        ("Hours",  {"fields": (("hours_subtotal", "hours_total"),)}),
        ("Totals", {"fields": (("amount_subtotal", "discount_total", "amount_tax", "amount_total"),)}),
        ("Deposit", {"fields": (("deposit_type", "deposit_value", "deposit_amount"), "remaining_due")}),
        ("Signing", {"fields": ("sign_token", "token_expires_at", "sign_link_preview", "sent_at", "viewed_at", "signed_at")}),
        # Remove "Validity" if your Proposal model doesn't have `valid_until`
        ("Validity", {"fields": ("valid_until",)}),
        ("Narrative (PDF)", {
            "fields": (
                "summary_md",
                "included_md",
                "overview_md",
                "addons_md",
                "maintenance_md",
                "payment_terms_md",
                "legal_terms_md",
            ),
            "classes": ("collapse",),
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = [
        mark_proposal_discount_verified,
        revoke_proposal_discount_verified,
        "action_generate_link",
        "action_mark_sent",
        "action_mark_signed",
        "action_mark_countersigned",
        "action_make_deposit_invoice",
        "action_create_project",
        "action_recompute_hours",
        "action_backfill_countersign",
        "action_email_pdf_only",
        "action_email_signup_only",
        "action_email_pdf_and_signup",
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "approver_user" and field is not None:
            try:
                field.queryset = field.queryset.filter(role__in=[User.Roles.OWNER, User.Roles.ADMIN, User.Roles.EMPLOYEE])
            except Exception:
                pass
        return field

    def get_form(self, request, obj=None, **kwargs):
        request._current_proposal_obj = obj
        return super().get_form(request, obj, **kwargs)

    def countersign_flag(self, obj):
        if not obj.countersign_required:
            return "—"
        if obj.countersigned_at:
            return "✔︎"
        if obj.signed_at:
            return "⚠︎ due"
        return "…"
    countersign_flag.short_description = "Countersign"

    def sign_link_preview(self, obj):
        if not obj.pk:
            return "-"
        url = obj.get_signing_url()
        if url and url.startswith("http"):
            return format_html('<a href="{}" target="_blank" rel="noopener">Open signing link</a>', url)
        return mark_safe(url or "-")
    sign_link_preview.short_description = "Signing URL"

    def sign_link_short(self, obj):
        if not obj.sign_token:
            return "-"
        return f"...{obj.sign_token[-8:]}"
    sign_link_short.short_description = "Sign token"

    def pdf_link(self, obj):
        try:
            if obj.pdf:
                return format_html('<a href="{}" target="_blank" rel="noopener">PDF</a>', obj.pdf.url)
        except Exception:
            pass
        return "—"
    pdf_link.short_description = "PDF"

    @admin.action(description="Email links → PDF only")
    def action_email_pdf_only(self, request, queryset):
        sent = 0
        skipped = 0
        for p in queryset:
            to_email = (p.contact_email or "").strip()
            if not to_email:
                skipped += 1
                continue
            if _send_links_email(p, to_email=to_email, include_pdf=True, include_signup=False):
                sent += 1
        if sent:
            self.message_user(request, f"Sent PDF link for {sent} proposal(s).", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped {skipped} proposal(s) without a contact email.", level=messages.WARNING)

    @admin.action(description="Email links → Account only")
    def action_email_signup_only(self, request, queryset):
        sent = 0
        skipped = 0
        for p in queryset:
            to_email = (p.contact_email or "").strip()
            if not to_email:
                skipped += 1
                continue
            if _send_links_email(p, to_email=to_email, include_pdf=False, include_signup=True):
                sent += 1
        if sent:
            self.message_user(request, f"Sent account link for {sent} proposal(s).", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped {skipped} proposal(s) without a contact email.", level=messages.WARNING)

    @admin.action(description="Email links → PDF + Account")
    def action_email_pdf_and_signup(self, request, queryset):
        sent = 0
        skipped = 0
        for p in queryset:
            to_email = (p.contact_email or "").strip()
            if not to_email:
                skipped += 1
                continue
            if _send_links_email(p, to_email=to_email, include_pdf=True, include_signup=True):
                sent += 1
        if sent:
            self.message_user(request, f"Sent PDF + account links for {sent} proposal(s).", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped {skipped} proposal(s) without a contact email.", level=messages.WARNING)

    @admin.action(description="Recompute Hours (subtotal/total)")
    def action_recompute_hours(self, request, queryset):
        updated = 0
        for p in queryset:
            sub = p.line_items.aggregate(s=Sum("line_hours"))["s"]
            if sub is None:
                sub = 0
                for li in p.line_items.all():
                    sub += (li.hours or 0) * (li.quantity or 0)
            sub = Decimal(sub or 0)
            tot = sub + Decimal("8.00")
            p.hours_subtotal = sub
            p.hours_total = tot
            p.save(update_fields=["hours_subtotal", "hours_total"])
            updated += 1
        self.message_user(request, f"Recomputed hours for {updated} proposal(s).", level=messages.SUCCESS)

    @admin.action(description="Generate signing link")
    def action_generate_link(self, request, queryset):
        n = 0
        for p in queryset:
            p.ensure_signing_link()
            n += 1
        self.message_user(request, f"Generated links for {n} proposal(s).", level=messages.SUCCESS)

    @admin.action(description="Mark sent (emails via hook)")
    def action_mark_sent(self, request, queryset):
        n = 0
        for p in queryset:
            p.mark_sent(actor=request.user, messenger_kwargs={"sender_user": request.user})
            n += 1
        self.message_user(request, f"Marked {n} proposal(s) as sent.", level=messages.SUCCESS)

    @admin.action(description="Mark signed (create deposit invoice)")
    @transaction.atomic
    def action_mark_signed(self, request, queryset):
        n = 0
        for p in queryset:
            p.mark_signed(actor=request.user)
            n += 1
        self.message_user(request, f"Marked {n} proposal(s) signed and created deposit invoice(s).", level=messages.SUCCESS)

    @admin.action(description="Mark countersigned")
    def action_mark_countersigned(self, request, queryset):
        n = 0
        for p in queryset:
            p.mark_countersigned(actor=request.user, save=True)
            n += 1
        self.message_user(request, f"Marked {n} proposal(s) as countersigned.", level=messages.SUCCESS)

    @admin.action(description="Create deposit invoice now")
    @transaction.atomic
    def action_make_deposit_invoice(self, request, queryset):
        created = 0
        for p in queryset:
            inv = p.create_deposit_invoice(actor=request.user)
            if inv is not None:
                created += 1
        self.message_user(request, f"Created {created} deposit invoice(s).", level=messages.SUCCESS)

    @admin.action(description="Create Project (from signed)")
    @transaction.atomic
    def action_create_project(self, request, queryset):
        created = 0
        skipped_unsigned = 0
        skipped_existing = 0

        for p in queryset:
            if not getattr(p, "signed_at", None):
                skipped_unsigned += 1
                continue

            if getattr(p, "projects", None) and p.projects.exists():
                skipped_existing += 1
                continue

            proj = p.create_project(
                actor=request.user,
                kickoff_today=True,
            )
            if proj:
                created += 1

        msg = f"Created {created} project(s)."
        if skipped_unsigned:
            msg += f" Skipped {skipped_unsigned} (not signed)."
            # noqa
        if skipped_existing:
            msg += f" Skipped {skipped_existing} (already had a project)."
        self.message_user(request, msg, level=messages.SUCCESS if created else messages.INFO)
