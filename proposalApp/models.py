# proposalApp/models.py
import os, uuid, datetime
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import secrets
from importlib import import_module
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from invoiceApp.models import Invoice


# ---------- Helpers ----------
MONEY = Decimal("0.01")
ALLOWED_PROPOSAL_PDF_EXTS = ["pdf"]
MAX_PROPOSAL_PDF_BYTES = 15 * 1024 * 1024  # 15 MB

def q2(v: Decimal) -> Decimal:
    if v is None:
        return Decimal("0.00")
    return (Decimal(v)).quantize(MONEY, rounding=ROUND_HALF_UP)

def validate_proposal_pdf_size(f):
    if f.size and f.size > MAX_PROPOSAL_PDF_BYTES:
        raise ValidationError(f"PDF too large (>{MAX_PROPOSAL_PDF_BYTES//1024//1024}MB).")

def proposal_pdf_upload_to(instance, filename):
    today = datetime.date.today()
    ext = os.path.splitext(filename)[1].lower()
    ext = ".pdf" if ext != ".pdf" else ext
    company_slug = getattr(getattr(instance, "company", None), "slug", None) or "proposal"
    return f"proposals/{today.year}/{today.month:02d}/{company_slug}-{uuid.uuid4().hex}{ext}"

def proof_upload_to(instance, filename):
    # Store in media/discount_proofs/YYYY/MM/<proposalId>/<filename>
    dt = timezone.now()
    return f"discount_proofs/{dt.year}/{dt.month:02}/{instance.id}/{filename}"

# ======================================================================
#                        REFERENCE TABLES
# ======================================================================

class JobRate(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "code")

    def __str__(self):
        return f"{self.name} @ {self.hourly_rate}"

class BaseSetting(models.Model):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=160)
    base_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return f"{self.name} (base {self.base_rate})"

class Discount(models.Model):
    class Kind(models.TextChoices):
        PERCENT = "PERCENT", "Percent"
        FIXED   = "FIXED",   "Fixed amount"

    name  = models.CharField(max_length=120)
    code  = models.SlugField(max_length=40, unique=True)
    kind  = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    requires_verification = models.BooleanField(default=False)
    stackable = models.BooleanField(default=False)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class CatalogItem(models.Model):
    code         = models.SlugField(max_length=80, unique=True)
    name         = models.CharField(max_length=160)
    description  = models.TextField(blank=True)
    job_rate     = models.ForeignKey(JobRate, on_delete=models.PROTECT, related_name="catalog_items")
    base_setting = models.ForeignKey(BaseSetting, on_delete=models.PROTECT, related_name="catalog_items")
    default_hours    = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    default_quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    is_active   = models.BooleanField(default=True)
    tags        = models.CharField(max_length=200, blank=True)
    sort_order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return f"{self.name} [{self.code}]"

class CostTier(models.Model):
    code        = models.SlugField(max_length=40, unique=True)
    label       = models.CharField(max_length=80)
    min_total   = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    max_total   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Leave blank for 'no upper limit'.")
    notes       = models.TextField(blank=True)
    sort_order  = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "min_total", "code")

    def __str__(self):
        hi = "∞" if self.max_total is None else f"{self.max_total:.2f}"
        return f"{self.label} ({self.min_total:.2f}–{hi})"

    def clean(self):
        # Basic sanity checks
        if self.max_total is not None and self.max_total <= self.min_total:
            raise ValidationError("max_total must be greater than min_total (or empty).")

    @classmethod
    def for_amount(cls, amount: Decimal):
        amount = Decimal(amount or 0)
        tier = (cls.objects.filter(is_active=True, min_total__lte=amount).filter(models.Q(max_total__isnull=True) | models.Q(max_total__gte=amount)).order_by("sort_order", "min_total").first())
        return tier


# ======================================================================
#                           DRAFT / CHECKLIST
# ======================================================================

class ProposalDraft(models.Model):
    class DepositType(models.TextChoices):
        NONE    = "NONE",    "None"
        PERCENT = "PERCENT", "Percent"
        FIXED   = "FIXED",   "Fixed"
    
    class ApprovalStatus(models.TextChoices):
        DRAFT     = "DRAFT",     "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED  = "APPROVED",  "Approved"
        REJECTED  = "REJECTED",  "Rejected"
        CONVERTED = "CONVERTED", "Converted"

    company = models.ForeignKey("companyApp.Company", on_delete=models.CASCADE, related_name="pricing_drafts")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approval_status = models.CharField(max_length=12, choices=ApprovalStatus.choices, default=ApprovalStatus.DRAFT, db_index=True,)
    title = models.CharField(max_length=200)
    currency = models.CharField(max_length=8, default="USD")
    contact_name = models.CharField(max_length=160, blank=True)
    contact_email = models.EmailField(blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.ForeignKey(Discount, null=True, blank=True, on_delete=models.SET_NULL)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    discount_requires_verification = models.BooleanField(default=False)
    is_discount_verified = models.BooleanField(default=False)
    verification_file = models.FileField(upload_to=proof_upload_to, null=True, blank=True)
    verification_note = models.CharField(max_length=240, blank=True)
    verification_checked_at = models.DateTimeField(null=True, blank=True)
    verification_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="proposal_drafts_verified"
    )

    total_hours = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    deposit_type  = models.CharField(max_length=10, choices=DepositType.choices, default=DepositType.NONE)
    deposit_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    remaining_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    estimate_tier = models.ForeignKey("CostTier", null=True, blank=True, on_delete=models.SET_NULL, related_name="drafts")
    estimate_low = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    estimate_high = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    estimate_manual = models.BooleanField(default=False, help_text="If checked, keep the selected tier and don't auto-update from totals.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    valid_until       = models.DateField(null=True, blank=True)
    summary_md        = models.TextField(blank=True)
    included_md       = models.TextField(blank=True)
    overview_md       = models.TextField(blank=True)
    addons_md         = models.TextField(blank=True)
    maintenance_md    = models.TextField(blank=True)
    payment_terms_md  = models.TextField(blank=True)
    legal_terms_md    = models.TextField(blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="proposal_drafts_approved")
    approval_notes = models.TextField(blank=True)
    assigned_reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="proposal_drafts_assigned", help_text="Admin/Owner assigned to review this draft.")

    class Meta:
        ordering = ("-created_at",)
    
    def autofill_contact_from_company(self, *, force: bool = False) -> None:
        if not self.company_id:
            return
        c = self.company
        if force or not (self.contact_name or "").strip():
            self.contact_name = (c.primary_contact_name or "").strip()
        if force or not (self.contact_email or "").strip():
            self.contact_email = (c.primary_email or "").strip()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.autofill_contact_from_company(force=False)
        super().save(*args, **kwargs)
        if self.discount_id:
            self.discount_requires_verification = bool(getattr(self.discount, "requires_verification", False))  # NEW
        super().save(*args, **kwargs)

    def mark_submitted(self, actor=None, save=True):
        name  = (self.company.primary_contact_name or "").strip() if self.company else ""
        email = (self.company.primary_email or "").strip() if self.company else ""
        if not name or not email:
            raise ValidationError(
                "Company must have a Primary Contact Name and Primary Email before submitting for approval."
            )
        self.approval_status = self.ApprovalStatus.SUBMITTED
        self.submitted_at = timezone.now()
        if save:
            self.save(update_fields=["approval_status", "submitted_at", "updated_at"])

    def mark_approved(self, actor=None, notes=None, save=True):
        self.approval_status = self.ApprovalStatus.APPROVED
        self.approved_at = timezone.now()
        if actor:
            self.approved_by = actor
        if notes:
            self.approval_notes = notes
        if save:
            self.save(update_fields=["approval_status", "approved_at", "approved_by", "approval_notes", "updated_at"])

    def mark_rejected(self, actor=None, notes=None, save=True):
        self.approval_status = self.ApprovalStatus.REJECTED
        if notes:
            self.approval_notes = notes
        if save:
            self.save(update_fields=["approval_status", "approval_notes", "updated_at"])

    def __str__(self):
        return f"Draft: {self.company.name} · {self.title}"

    def compute_line_total(self, *, hours, qty, job_rate: "JobRate", base_setting: "BaseSetting") -> Decimal:
        hours = Decimal(hours or 0)
        qty   = Decimal(qty or 0)
        hr    = Decimal(job_rate.hourly_rate if job_rate else 0)
        base  = Decimal(base_setting.base_rate if base_setting else 0)
        return q2((hours * qty * hr) + base)

    def compute_discount_amount(self, base: Decimal) -> Decimal:
        base = q2(base or 0)
        if not self.discount or not self.discount.is_active:
            return Decimal("0.00")
        if self.discount.kind == Discount.Kind.PERCENT:
            amt = q2(base * (self.discount.value or 0) / Decimal("100"))
        amt = q2(self.discount.value or 0)
        # Cap at base
        return amt if amt <= base else base

    def compute_deposit_amount(self, grand_total: Decimal) -> Decimal:
        if self.deposit_type == self.DepositType.PERCENT:
            return q2((grand_total or 0) * (self.deposit_value or 0) / Decimal("100"))
        if self.deposit_type == self.DepositType.FIXED:
            return q2(self.deposit_value or 0)
        return Decimal("0.00")
    
    def update_estimate_from_tiers(self, *, use_total=True, save=True):
        amount = self.total if use_total else self.subtotal

        if self.estimate_manual and self.estimate_tier_id:
            tier = self.estimate_tier
        else:
            tier = CostTier.for_amount(amount)
            self.estimate_tier = tier

        if tier:
            self.estimate_low = tier.min_total or Decimal("0.00")
            self.estimate_high = tier.max_total or amount
        else:
            self.estimate_low = Decimal("0.00")
            self.estimate_high = Decimal("0.00")

        if save:
            self.save(update_fields=["estimate_tier", "estimate_low", "estimate_high", "updated_at"])
        return tier

    def recalc_totals(self, *, save=True):
        hours_expr = ExpressionWrapper(
            F("hours") * F("quantity"),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
        agg = self.items.aggregate(
            hours_sum=Sum(hours_expr),
            money_sum=Sum("line_total"),
        )

        self.total_hours = (agg["hours_sum"] or Decimal("0.00"))

        line_sum = q2(agg["money_sum"] or Decimal("0.00"))
        self.subtotal = line_sum

        discount_allowed = False
        if self.discount and self.discount.is_active:
            if getattr(self.discount, "requires_verification", False):
                discount_allowed = bool(self.is_discount_verified)
            else:
                discount_allowed = True
        
        disc_amt = self.compute_discount_amount(self.subtotal) if discount_allowed else Decimal("0.00")
        if disc_amt > self.subtotal:
            disc_amt = self.subtotal
        self.discount_amount = q2(disc_amt)

        # self.discount_amount = q2(self.compute_discount_amount(self.subtotal)) if discount_allowed else Decimal("0.00")

        base_total = q2(self.subtotal - self.discount_amount)
        if base_total < Decimal("0.00"):
            base_total = Decimal("0.00")

        self.total = base_total

        pre_discount_for_deposit = self.subtotal
        deposit_calc = q2(self.compute_deposit_amount(pre_discount_for_deposit))

        if base_total <= Decimal("0.00"):
            deposit_calc = Decimal("0.00")

        if deposit_calc > self.total:
            deposit_calc = self.total

        self.deposit_amount = deposit_calc
        self.remaining_due  = q2(base_total - deposit_calc)

        if save:
            self.save(update_fields=[
                "total_hours", "subtotal", "discount_amount", "total",
                "deposit_amount", "remaining_due", "discount_requires_verification", "updated_at"
            ])

        self.update_estimate_from_tiers(save=True)
        return self.total

    @transaction.atomic
    def convert_to_proposal(self, *, actor=None):
        self.recalc_totals(save=True)
        snap_name  = (self.contact_name or "").strip() or (self.company.primary_contact_name or "")
        snap_email = (self.contact_email or "").strip() or (self.company.primary_email or "")

        hours_sub = self.total_hours or Decimal("0.00")
        hours_tot = hours_sub + Decimal("8.00")

        prop = Proposal.objects.create(
            company=self.company,
            created_by=actor,
            title=self.title,
            currency=self.currency,
            amount_subtotal=self.subtotal,
            amount_tax=Decimal("0.00"),
            discount_total=self.discount_amount,
            amount_total=self.total,
            deposit_type=self.deposit_type,
            deposit_value=self.deposit_value,
            deposit_amount=self.deposit_amount,
            remaining_due=self.remaining_due,
            converted_from=self,
            contact_name=snap_name,
            contact_email=snap_email,
            hours_subtotal=hours_sub,
            hours_total=hours_tot,
        )
        if self.approved_by_id and not getattr(prop, "approver_user_id", None):
            prop.approver_user_id = self.approved_by_id
            prop.save(update_fields=["approver_user"])

        for li in self.items.all().order_by("sort_order", "pk"):
            ProposalLineItem.objects.create(
                proposal=prop,
                sort_order=li.sort_order,
                name=li.name,
                description=li.description,
                hours=li.hours,
                quantity=li.quantity,
                job_rate=li.job_rate,
                base_setting=li.base_setting,
                line_total=li.line_total,
                unit_price=li.line_total,
                subtotal=li.line_total,
                line_hours=(li.hours or Decimal("0.00")) * (li.quantity or Decimal("0.00")),
            )

        if self.discount:
            pending = getattr(self.discount, "requires_verification", False) and not self.is_discount_verified
            ProposalAppliedDiscount.objects.create(
                proposal=prop,
                discount_code=self.discount.code,
                name=self.discount.name,
                kind=self.discount.kind,
                value=self.discount.value,
                amount_applied=self.discount_amount,
                sort_order=0,
                requires_verification=getattr(self.discount, "requires_verification", False),
                pending_verification=pending,
            )
        
        if self.discount:
            prop.discount_requires_verification = bool(getattr(self.discount, "requires_verification", False))
            prop.is_discount_verified = bool(self.is_discount_verified)
            if self.verification_file:
                prop.verification_file = self.verification_file
            prop.verification_note = self.verification_note or ""
            prop.verification_checked_at = self.verification_checked_at
            prop.verification_checked_by = self.verification_checked_by
            prop.save(update_fields=[
                "discount_requires_verification", "is_discount_verified",
                "verification_file", "verification_note",
                "verification_checked_at", "verification_checked_by",
            ])

        for n in self.notes.all().order_by("sort_order", "pk"):
            ProposalSection.objects.create(
                proposal=prop,
                sort_order=n.sort_order,
                subject=n.subject,
                body_md=n.body_md,
            )
        
        for idx, n in enumerate(self.notes.all().order_by("sort_order", "pk")):
            ProposalNote.objects.create(
                proposal=prop,
                subject=(n.subject or "").strip(),
                body_md=(n.body_md or "").strip(),
                sort_order=idx,
                is_visible_to_client=True,
            )
        
        summary_text = (self.summary_md or "").strip()
        if summary_text:
            ProposalSummary.objects.update_or_create(
                proposal=prop,
                defaults={"body_md": summary_text, "is_visible_to_client": True},
            )

        self.approval_status = self.ApprovalStatus.CONVERTED
        self.save(update_fields=["approval_status", "updated_at"])
        ProposalEvent.objects.create(proposal=prop, kind=ProposalEvent.Kind.CREATED, actor=actor)
        return prop
    
    @property
    def valid_until_effective(self):
        base = self.created_at or timezone.now()
        return (self.valid_until or (base + timedelta(days=30))).date()

class DraftNote(models.Model):
    draft = models.ForeignKey("ProposalDraft", on_delete=models.CASCADE, related_name="notes")
    sort_order = models.PositiveIntegerField(default=0)
    subject = models.CharField(max_length=160)
    body_md = models.TextField(blank=True)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"{self.draft} · {self.subject}"

class DraftItem(models.Model):
    draft = models.ForeignKey(ProposalDraft, on_delete=models.CASCADE, related_name="items")

    catalog_item = models.ForeignKey(
        "CatalogItem",
        on_delete=models.PROTECT,
        related_name="draft_items",
        help_text="Choose from the predefined items list."
    )

    name         = models.CharField(max_length=160)
    description  = models.TextField(blank=True)

    job_rate     = models.ForeignKey(JobRate, on_delete=models.PROTECT, related_name="draft_items")
    base_setting = models.ForeignKey(BaseSetting, on_delete=models.PROTECT, related_name="draft_items")

    hours    = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))

    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"{self.name} · {self.draft}"
    
    @property
    def line_hours(self):
        return (self.hours or Decimal("0.00")) * (self.quantity or Decimal("0.00"))

    def _apply_catalog(self):
        c = self.catalog_item
        if not c:
            return
        self.name = c.name
        self.description = c.description
        self.job_rate = c.job_rate
        self.base_setting = c.base_setting

    def save(self, *args, **kwargs):
        creating = not bool(self.pk)

        self._apply_catalog()

        if creating:
            if (self.hours is None) or (self.hours == Decimal("0.00")) or (self.hours == Decimal("1.00")):
                self.hours = self.catalog_item.default_hours
            if (self.quantity is None) or (self.quantity == Decimal("0.00")) or (self.quantity == Decimal("1.00")):
                self.quantity = self.catalog_item.default_quantity

        self.line_total = self.draft.compute_line_total(
            hours=self.hours,
            qty=self.quantity,
            job_rate=self.job_rate,
            base_setting=self.base_setting,
        )

        super().save(*args, **kwargs)

        self.draft.recalc_totals(save=True)


# ======================================================================
#                             PROPOSAL (FINAL)
# ======================================================================

def _signing_base() -> str:
    return getattr(settings, "PROPOSAL_SIGNING_URL_BASE", "").rstrip("/")

class Proposal(models.Model):
    company     = models.ForeignKey("companyApp.Company", on_delete=models.CASCADE, related_name="simple_proposals")
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    contact_name = models.CharField(max_length=160, blank=True)
    contact_email = models.EmailField(blank=True)

    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="ProposalViewer", related_name="proposals_shared_with", blank=True,)

    def __str__(self):
        return f"Proposal {self.code} — {self.company.name}"

    title       = models.CharField(max_length=200)
    currency    = models.CharField(max_length=8, default="USD")

    hours_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    hours_total    = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    amount_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_tax      = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_total    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    discount_requires_verification = models.BooleanField(default=False)
    is_discount_verified = models.BooleanField(default=False)
    verification_file = models.FileField(upload_to=proof_upload_to, null=True, blank=True)
    verification_note = models.CharField(max_length=240, blank=True)
    verification_checked_at = models.DateTimeField(null=True, blank=True)
    verification_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="proposals_verified"
    )

    deposit_type   = models.CharField(max_length=10, default=ProposalDraft.DepositType.NONE, choices=ProposalDraft.DepositType.choices)
    deposit_value  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    remaining_due  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    converted_from = models.ForeignKey(ProposalDraft, null=True, blank=True, on_delete=models.SET_NULL, related_name="proposals")

    pdf = models.FileField(upload_to=proposal_pdf_upload_to, null=True, blank=True, validators=[FileExtensionValidator(ALLOWED_PROPOSAL_PDF_EXTS), validate_proposal_pdf_size], help_text="Upload a finalized PDF; optional if you generate on the fly.")

    sign_token       = models.CharField(max_length=64, unique=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    sent_at    = models.DateTimeField(null=True, blank=True)
    viewed_at  = models.DateTimeField(null=True, blank=True)
    signed_at  = models.DateTimeField(null=True, blank=True)

    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="proposals_to_countersign",
        help_text="Employee who approved the draft and should countersign after client signs."
    )
    countersign_required = models.BooleanField(
        default=True,
        help_text="If true, an internal countersign is required after the client signs."
    )
    countersigned_at = models.DateTimeField(null=True, blank=True)
    countersigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="proposals_countersigned"
    )
    countersign_notes = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.company.name} · {self.title}"

    def ensure_signing_link(self, *, hours_valid: int = 336):  # default 14 days
        if not self.sign_token:
            self.sign_token = secrets.token_urlsafe(32)  # ~43 chars, fits in 64
        if not self.token_expires_at:
            self.token_expires_at = timezone.now() + timezone.timedelta(hours=hours_valid)
        self.save(update_fields=["sign_token", "token_expires_at", "updated_at"])
        base = _signing_base()
        return f"{base}/{self.sign_token}" if base else self.sign_token

    def get_signing_url(self) -> str:
        base = _signing_base()
        if not self.sign_token:
            self.ensure_signing_link()
        return f"{base}/{self.sign_token}" if base else self.sign_token

    def mark_sent(self, *, actor=None, messenger_kwargs: dict | None = None, skip_messenger: bool = False):
        self.ensure_signing_link()
        if not self.sent_at:
            self.sent_at = timezone.now()
        self.save(update_fields=["sent_at", "updated_at"])

        if not skip_messenger:
            hook_path = getattr(settings, "PROPOSAL_MESSENGER", "")
            if hook_path:
                try:
                    if ":" in hook_path:
                        mod_path, fn_name = hook_path.split(":", 1)
                    else:
                        mod_path, fn_name = hook_path.rsplit(".", 1)
                    mod = __import__(mod_path, fromlist=[fn_name])
                    hook = getattr(mod, fn_name)
                    emails = list(self.recipients.values_list("email", flat=True)) or []
                    hook(self, emails, self.get_signing_url(), **(messenger_kwargs or {}))
                except Exception as e:
                    ProposalEvent.objects.create(
                        proposal=self, kind=ProposalEvent.Kind.UPDATED, actor=actor,
                        data={"warning": f"Messenger hook failed: {e!r}"}
                    )

        ProposalEvent.objects.create(proposal=self, kind=ProposalEvent.Kind.SENT, actor=actor)
        return self.sent_at

    def mark_viewed(self, *, ip=None, actor=None):
        first = False
        if not self.viewed_at:
            first = True
            self.viewed_at = timezone.now()
            self.save(update_fields=["viewed_at", "updated_at"])
        ProposalEvent.objects.create(
            proposal=self, kind=ProposalEvent.Kind.VIEWED, actor=actor,
            ip_address=ip, data={"first_time": first}
        )
        return first

    def create_deposit_invoice(self, *, actor=None, due_date=None, customer_user=None):
        if q2(self.amount_total) <= Decimal("0.00") or q2(self.deposit_amount) <= Decimal("0.00"):
            return None

        return Invoice.from_proposal(
            self,
            created_by=actor,
            due_date=due_date,
            customer_user=customer_user,
        )
    
    def mark_signed(self, *, actor=None, ip=None, signature_payload=None, due_date=None, customer_user=None):
        if not self.signed_at:
            self.signed_at = timezone.now()
            self.save(update_fields=["signed_at", "updated_at"])

        self.create_deposit_invoice(actor=actor, due_date=due_date, customer_user=customer_user)

        ProposalEvent.objects.create(
            proposal=self, kind=ProposalEvent.Kind.SIGNED, actor=actor,
            ip_address=ip, data={"signature": signature_payload}
        )
        return self.signed_at
    
    def get_signature_info(self):
        """
        Returns {"signed_at": datetime|None, "signer_name": str|None}.
        Pulls the most recent SIGNED event and reads the payload you already store.
        """
        ev = self.events.filter(kind=ProposalEvent.Kind.SIGNED).order_by("-at").first()
        signer_name = None
        if ev and ev.data:
            # mark_signed(...) stored payload under data["signature"]
            payload = ev.data.get("signature") or ev.data
            signer_name = (payload.get("full_name") or payload.get("name") or "").strip() or None
        return {"signed_at": self.signed_at, "signer_name": signer_name}

    def create_deposit_invoice(self, *, actor=None, due_date=None, customer_user=None):
        from invoiceApp.models import Invoice

        inv = Invoice.from_proposal(
            self,
            created_by=actor,
            due_date=due_date,
            customer_user=customer_user,
        )
        return inv
    
    @property
    def countersign_due(self) -> bool:
        return bool(self.countersign_required and self.signed_at and not self.countersigned_at)

    def mark_countersigned(self, actor=None, notes=None, save=True):
        self.countersigned_at = timezone.now()
        if actor:
            self.countersigned_by = actor
        if notes:
            self.countersign_notes = (self.countersign_notes + "\n" if self.countersign_notes else "") + str(notes)
        if save:
            self.save(update_fields=["countersigned_at", "countersigned_by", "countersign_notes", "updated_at"])
    
    def create_project(self, *, actor=None, manager=None, kickoff_today=False, name=None):
        from projectApp.models import Project
        from django.utils import timezone

        existing = getattr(self, "projects", None)
        if existing and existing.exists():
            return existing.order_by("pk").first()

        mgr = manager or getattr(self, "approver_user", None) or getattr(self, "created_by", None) or actor
        if not (getattr(mgr, "is_staff", False) or getattr(mgr, "is_superuser", False)):
            mgr = None

        base = (name or self.title or "Project").strip()[:200]
        unique_name = base
        i = 2
        while Project.objects.filter(company=self.company, name=unique_name).exists():
            unique_name = f"{base} ({i})"
            i += 1

        with transaction.atomic():
            kwargs = dict(
                company=self.company,
                proposal=self,
                name=unique_name,
                created_by=actor or getattr(self, "created_by", None),
            )
            if mgr:
                kwargs["manager"] = mgr
            if kickoff_today:
                kwargs["start_date"] = timezone.now().date()

            proj = Project.objects.create(**kwargs)
            return proj

class ProposalNote(models.Model):
    proposal = models.ForeignKey("Proposal", related_name="notes", on_delete=models.CASCADE)
    subject = models.CharField(max_length=160, blank=True)
    body_md = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible_to_client = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return self.subject or f"Note #{self.pk}"
    
class ProposalSummary(models.Model):
    proposal = models.OneToOneField("Proposal", related_name="summary", on_delete=models.CASCADE)
    body_md = models.TextField(blank=True)
    is_visible_to_client = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary for {self.proposal_id}"

class ProposalLineItem(models.Model):
    proposal     = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="line_items")
    sort_order   = models.PositiveIntegerField(default=0)

    name         = models.CharField(max_length=160)
    description  = models.TextField(blank=True)

    hours        = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    quantity     = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    job_rate     = models.ForeignKey(JobRate, on_delete=models.PROTECT, related_name="proposal_items")
    base_setting = models.ForeignKey(BaseSetting, on_delete=models.PROTECT, related_name="proposal_items")
    line_total   = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_hours = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    unit_price   = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal     = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"{self.name} ({self.line_total})"

class ProposalSection(models.Model):
    proposal = models.ForeignKey("Proposal", on_delete=models.CASCADE, related_name="sections")
    sort_order = models.PositiveIntegerField(default=0)
    subject = models.CharField(max_length=160)
    body_md = models.TextField(blank=True)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"{self.proposal} · {self.subject}"

class ProposalAppliedDiscount(models.Model):
    proposal       = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="applied_discounts")
    discount_code  = models.SlugField(max_length=40)
    name           = models.CharField(max_length=120)
    kind           = models.CharField(max_length=10, choices=Discount.Kind.choices)
    value          = models.DecimalField(max_digits=10, decimal_places=2)
    amount_applied = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sort_order     = models.PositiveIntegerField(default=0)

    requires_verification = models.BooleanField(default=False)
    pending_verification  = models.BooleanField(default=False)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"{self.name} ({self.discount_code})"

class ProposalRecipient(models.Model):
    proposal    = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="recipients")
    name        = models.CharField(max_length=160, blank=True)
    email       = models.EmailField()
    is_primary  = models.BooleanField(default=True)
    delivered_at   = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-is_primary", "email")
        unique_together = (("proposal", "email"),)

    def __str__(self):
        return f"{self.email} · {self.proposal}"
    
class ProposalViewer(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="allowed_viewers")
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="allowed_proposals")

    class Meta:
        unique_together = [("proposal", "user")]
        indexes = [models.Index(fields=["proposal", "user"])]

    def __str__(self):
        return f"{self.user} can view {self.proposal}"

class ProposalEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED  = "CREATED",  "Created"
        SENT     = "SENT",     "Sent"
        VIEWED   = "VIEWED",   "Viewed"
        SIGNED   = "SIGNED",   "Signed"
        UPDATED  = "UPDATED",  "Updated"
        COMMENT  = "COMMENT",  "Comment"

    proposal   = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="events")
    kind       = models.CharField(max_length=20, choices=Kind.choices)
    at         = models.DateTimeField(auto_now_add=True)
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    data       = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ("-at", "pk")

    def __str__(self):
        return f"{self.proposal} · {self.kind} @ {self.at:%Y-%m-%d %H:%M}"
