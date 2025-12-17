# companyApp/models.py
import os
import uuid
import datetime

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.templatetags.static import static
from django.utils.text import slugify
from django.utils import timezone

from . import uploads

User = settings.AUTH_USER_MODEL

# ---------- Logo helpers ----------

ALLOWED_LOGO_EXTS = ["jpg", "jpeg", "png", "webp"]
MAX_LOGO_BYTES = 3 * 1024 * 1024  # 3 MB

def validate_logo_size(f):
    if f.size and f.size > MAX_LOGO_BYTES:
        raise ValidationError(f"Logo too large (>{MAX_LOGO_BYTES // 1024 // 1024}MB).")

def logo_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".") or "png"
    if ext not in ALLOWED_LOGO_EXTS:
        ext = "png"
    today = datetime.date.today()
    base = slugify(getattr(instance, "slug", "") or getattr(instance, "name", "") or "company")
    return f"company_logos/{today.year}/{today.month:02d}/{base}-{uuid.uuid4().hex}.{ext}"


# =======================================================================
#                              COMPANY
# =======================================================================

class Company(models.Model):
    class Status(models.TextChoices):
        PROSPECT = "PROSPECT", "Prospect"
        CONVERTED_PROSPECT = "CONVERTED_PROSPECT", "Converted Prospect"
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        LOST = "LOST", "Lost"

    class PipelineStatus(models.TextChoices):
        NEW = "NEW", "New"
        HOLDING = "HOLDING", "Holding"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ONGOING = "ONGOING", "On Going"
        FINISHED = "FINISHED", "Finished"
        INACTIVE = "INACTIVE", "Inactive"
        LOST = "LOST", "Lost"

    class WorkStatus(models.TextChoices):
        NONE = "NONE", "Not Started"
        DISCOVERY = "DISCOVERY", "Discovery / Intake"
        PROPOSAL_SENT = "PROPOSAL_SENT", "Proposal Sent"
        PROPOSAL_APPROVED = "PROPOSAL_APPROVED", "Proposal Approved"
        ROAD_MAP_SENT = "ROAD_MAP_SENT", "Road Map Sent"
        DEPOSIT_INVOICE_SENT = "DEPOSIT_INVOICE_SENT", "Deposit Invoice Sent"
        DEPOSIT_PAID = "DEPOSIT_PAID", "Deposit Paid"
        PROJECT_SCHEDULED = "PROJECT_SCHEDULED", "Project Scheduled"
        DESIGN_STARTED = "DESIGN_STARTED", "Design Started"
        DESIGN_APPROVED = "DESIGN_APPROVED", "Design Approved"
        DEVELOPMENT_STARTED = "DEVELOPMENT_STARTED", "Development Started"
        QA_REVIEW = "QA_REVIEW", "QA / Review"
        DEVELOPMENT_APPROVED = "DEVELOPMENT_APPROVED", "Development Approved"
        READY_FOR_LAUNCH = "READY_FOR_LAUNCH", "Ready for Launch"
        LIVE = "LIVE", "Site Live"
        FINAL_INVOICE_SENT = "FINAL_INVOICE_SENT", "Final Invoice Sent"
        FINAL_INVOICE_PAID = "FINAL_INVOICE_PAID", "Final Invoice Paid"
        RECURRING_INVOICE_SENT = "RECURRING_INVOICE_SENT", "Recurring Invoice Sent"
        RECURRING_INVOICE_PAID = "RECURRING_INVOICE_PAID", "Recurring Invoice Paid"
        ON_HOLD = "ON_HOLD", "On Hold"
    
    class ProjectPhase(models.TextChoices):
        NONE = "NONE", "Not Started"
        DISCOVERY = "DISCOVERY", "Discovery"
        DESIGN = "DESIGN", "Design"
        DEVELOPMENT = "DEVELOPMENT", "Development"
        TESTING = "TESTING", "Testing / QA"
        LAUNCH = "LAUNCH", "Launch"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    users = models.ManyToManyField(
        User,
        through="CompanyMember",
        related_name="companies",
        blank=True,
    )

    primary_contact_name = models.CharField(max_length=120, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state_region = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=120, blank=True, default="USA")

    website = models.URLField(blank=True)

    logo = models.ImageField(
        upload_to=logo_upload_to,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(ALLOWED_LOGO_EXTS), validate_logo_size],
        help_text="PNG/JPEG/WebP, up to 3MB.",
    )
    logo_external_url = models.URLField(
        blank=True,
        help_text="Optional external logo URL (e.g., Google Drive shared link).",
    )

    consultation_sheet_url = models.URLField(
        blank=True,
        help_text="Link to internal consultation / project sheet (BeeDev-only).",
    )

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    pipeline_status = models.CharField(
        max_length=24,
        choices=PipelineStatus.choices,
        blank=True,
        default=PipelineStatus.NEW,
    )
    work_status = models.CharField(
        max_length=40,
        choices=WorkStatus.choices,
        default=WorkStatus.NONE,
        help_text="Micro status for current work state (e.g., design started, deposit invoice sent).",
    )
    project_phase = models.CharField(
        max_length=20,
        choices=ProjectPhase.choices,
        default=ProjectPhase.NONE,
    )
    project_phase_updated_at = models.DateTimeField(null=True, blank=True)

    prospect = models.OneToOneField(
        "prospectApp.Prospect",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company",
        help_text="Original prospect record, if applicable.",
    )

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="companies_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["pipeline_status"]),
            models.Index(fields=["work_status"]),
            models.Index(fields=["project_phase"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            old = Company.objects.filter(pk=self.pk).values("project_phase").first()
            if old and old["project_phase"] != self.project_phase:
                self.project_phase_updated_at = timezone.now()
        else:
            if self.project_phase and self.project_phase != Company.ProjectPhase.NONE:
                self.project_phase_updated_at = timezone.now()

        if not self.slug:
            base = slugify(self.name) or "company"
            slug = base
            i = 2
            while Company.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def logo_url(self) -> str:
        if getattr(self, "logo_external_url", ""):
            return self.logo_external_url
        try:
            if self.logo:
                return self.logo.url
        except Exception:
            pass
        return static("img/company-logo-placeholder.svg")

    @property
    def has_client_users(self) -> bool:
        from userApp.models import User as AppUser
        return self.members.filter(
            is_active=True,
            member_type=CompanyMember.MemberType.CLIENT,
            user__role=AppUser.Roles.CLIENT,
        ).exists()


# =======================================================================
#                          COMPANY MEMBER
# =======================================================================

class CompanyMember(models.Model):
    class MemberType(models.TextChoices):
        CLIENT = "CLIENT", "Client Contact"
        STAFF = "STAFF", "Staff"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )

    member_type = models.CharField(
        max_length=10,
        choices=MemberType.choices,
        default=MemberType.CLIENT,
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary point of contact for this company.",
    )
    is_active = models.BooleanField(default=True)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "user")
        indexes = [
            models.Index(fields=["company", "user", "is_active"]),
            models.Index(fields=["company", "member_type"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.company} ({self.member_type})"


# =======================================================================
#                         PROPOSAL & ROADMAP & INVOICE
# =======================================================================

class ProposalDocument(models.Model):
    company = models.ForeignKey(
        "companyApp.Company",
        on_delete=models.CASCADE,
        related_name="proposals",
    )

    title = models.CharField(max_length=255, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    file = models.FileField(upload_to=uploads.proposals_upload_to, blank=True, null=True)
    external_url = models.URLField(blank=True)

    visible_to_client = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposals_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=Q(is_active=True),
                name="one_active_proposal_per_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "visible_to_client"]),
        ]

    def __str__(self):
        label = self.title or f"Proposal v{self.version}"
        return f"{self.company} · {label}"

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Provide a proposal file or an external URL.")

class RoadMap(models.Model):
    company = models.ForeignKey(
        "companyApp.Company",
        on_delete=models.CASCADE,
        related_name="roadmaps",
    )

    title = models.CharField(max_length=255, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    file = models.FileField(upload_to=uploads.roadmaps_upload_to, blank=True, null=True)
    external_url = models.URLField(blank=True)

    visible_to_client = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roadmaps_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=Q(is_active=True),
                name="one_active_roadmap_per_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "visible_to_client"]),
        ]

    def __str__(self):
        label = self.title or f"Roadmap v{self.version}"
        return f"{self.company} · {label}"

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Provide a roadmap file or an external URL.")

class Invoice(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    invoice_number = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)

    file = models.FileField(upload_to=uploads.invoices_upload_to, blank=True, null=True)

    external_url = models.URLField(blank=True)

    visible_to_client = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-paid_at", "-created_at"]
        indexes = [
            models.Index(fields=["company", "visible_to_client"]),
            models.Index(fields=["company", "paid_at"]),
        ]

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Provide an invoice file or an external URL.")


# =======================================================================
#                              AGREEMENTS
# =======================================================================

class Agreement(models.Model):
    class Kind(models.TextChoices):
        CSA = "CSA", "Client Services Agreement"
        SOW = "SOW", "Statement of Work"
        NDA = "NDA", "Non-Disclosure Agreement"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent for Signature"
        SIGNED = "SIGNED", "Fully Signed"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        TERMINATED = "TERMINATED", "Terminated"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="agreements",
    )
    kind = models.CharField(
        max_length=12,
        choices=Kind.choices,
        default=Kind.SOW,
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional friendly title (e.g., 'Website Rebuild SOW').",
    )

    file_signed = models.FileField(
        upload_to=uploads.agreements_signed_upload_to,
        help_text="Final signed PDF (downloaded from BoldSign or other provider).",
    )
    file_source = models.FileField(
        upload_to=uploads.agreements_source_upload_to,
        blank=True,
        null=True,
        help_text="(Optional) original doc or unsigned PDF.",
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.SIGNED,
    )
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="superseded_by",
    )

    effective_date = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)

    signed_by_name = models.CharField(max_length=120, blank=True)
    signed_by_email = models.EmailField(blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    countersigned_by = models.CharField(max_length=120, blank=True)
    countersigned_at = models.DateTimeField(null=True, blank=True)

    esign_provider = models.CharField(
        max_length=60,
        blank=True,
        help_text="e.g., 'BoldSign', 'DocuSign', etc.",
    )
    esign_envelope_id = models.CharField(
        max_length=120,
        blank=True,
        help_text="Provider-specific ID (e.g., BoldSign document ID).",
    )
    esign_view_url = models.URLField(
        blank=True,
        help_text="Link to the provider's hosted document/view.",
    )

    visible_to_client = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="agreements_uploaded",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "kind"]),
        ]

    def __str__(self):
        base = self.title or f"{self.get_kind_display()} v{self.version}"
        return f"{self.company.name} · {base}"

    @property
    def is_active(self):
        return (
            self.status in {self.Status.SIGNED}
            and (not self.expires_at or self.expires_at >= timezone.now().date())
        )


# =======================================================================
#                            COMPANY LINK TYPES
# =======================================================================

class CompanyLinkType(models.Model):
    key = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Internal key (e.g. 'preview', 'social', 'assets_folder').",
    )
    label = models.CharField(
        max_length=100,
        help_text="Human label shown in the UI, e.g. 'Preview Link'.",
    )
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(
        default=100,
        help_text="Lower numbers appear first.",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Protect system types from accidental deletion.",
    )

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self) -> str:
        return self.label


# =======================================================================
#                              COMPANY LINKS
# =======================================================================

class CompanyLink(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="links",
    )
    link_type = models.ForeignKey(
        CompanyLinkType,
        on_delete=models.PROTECT,
        related_name="links",
    )

    title = models.CharField(
        max_length=255,
        help_text="Short label, e.g. 'Staging Site' or 'Instagram'.",
    )
    url = models.URLField(max_length=500)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_links_created",
    )

    notes = models.TextField(blank=True)

    visible_to_client = models.BooleanField(
        default=True,
        help_text="If unchecked, only staff sees this link in the portal.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["link_type__sort_order", "title"]
        indexes = [
            models.Index(fields=["company", "visible_to_client", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.name} · {self.title}"


# =======================================================================
#                         PROJECT UPDATES
# =======================================================================

class CompanyUpdateLog(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    title = models.CharField(max_length=255)
    body = models.TextField()

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_updates",
    )
    visible_to_client = models.BooleanField(default=True)

    pinned = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pinned", "-created_at"]

    def __str__(self):
        return f"[{self.company.name}] {self.title}"


# =======================================================================
#                         PORTAL INVITES
# =======================================================================

class PortalInvite(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="invites",
    )
    prospect = models.ForeignKey(
        "prospectApp.Prospect",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portal_invites",
        help_text="Original prospect record, if applicable.",
    )

    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="portal_invites_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite for {self.email} ({self.company.name})"

    @property
    def is_valid(self) -> bool:
        return (not self.used) and timezone.now() < self.expires_at
