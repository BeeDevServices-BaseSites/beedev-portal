# prospectApp/models.py

from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

User = settings.AUTH_USER_MODEL


# =======================================================================
#                         BASE TIMESTAMPED MODEL
# =======================================================================

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def _coalesce(*vals):
    for v in vals:
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""


# =======================================================================
#                              PROSPECT
# =======================================================================

class Prospect(TimeStamped):

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        QUALIFIED = "QUALIFIED", "Qualified"
        PROPOSAL_SENT = "PROPOSAL_SENT", "Proposal Sent"
        DEPOSIT_PENDING = "DEPOSIT_PENDING", "Deposit Pending"
        DEPOSIT_PAID = "DEPOSIT_PAID", "Deposit Paid"
        CLOSED_LOST = "CLOSED_LOST", "Closed / Lost"

    full_name = models.CharField(max_length=120, blank=True)
    company_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=40, blank=True)

    address1 = models.CharField(max_length=160, blank=True)
    address2 = models.CharField(max_length=160, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=60, blank=True, default="USA")

    website_url = models.URLField(
        max_length=300,
        blank=True,
        help_text="Leave blank if no site.",
    )

    sheet_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Link to external sheet/record for this prospect.",
    )

    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
    )

    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated tags (optional).",
    )

    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects_created",
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects_updated",
    )

    def save(self, *args, **kwargs):
        # Normalize email
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        base = self.company_name or self.full_name or self.email
        return f"{base} ({self.email})"

    @property
    def has_website(self) -> bool:
        return bool(self.website_url)

    @property
    def company(self):
        """
        Convenience accessor:
        If a Company has been created and linked, return it.
        (Company model has a OneToOneField back to Prospect.)
        """
        return getattr(self, "company", None)

    # -------------------------------------------------------------------
    # Helper: create/update Company when ready
    # -------------------------------------------------------------------

    @transaction.atomic
    def create_or_update_company(self, *, actor=None):

        from companyApp.models import Company  # local import to avoid cycles

        company_name = _coalesce(
            self.company_name,
            self.full_name,
            self.email.split("@")[0],
            "Unnamed Company",
        )

        contact_name = _coalesce(
            self.full_name,
        )

        contact_email = (self.email or "").strip().lower()

        # Prefer linking via the OneToOne prospect field.
        company, created = Company.objects.get_or_create(
            prospect=self,
            defaults={
                "name": company_name,
                "primary_contact_name": contact_name,
                "primary_contact_email": contact_email,
                "phone": self.phone or "",
                "website": self.website_url or "",
                "status": Company.Status.CONVERTED_PROSPECT,
                "pipeline_status": Company.PipelineStatus.NEW,
                "work_status": Company.WorkStatus.DEPOSIT_PAID
                if self.status == self.Status.DEPOSIT_PAID
                else Company.WorkStatus.NONE,
                "consultation_sheet_url": self.sheet_url or "",
                "created_by": actor,
            },
        )

        # If company already existed for this prospect, we only do light fills.
        if not created:
            fields_to_update = []

            if not company.primary_contact_name and contact_name:
                company.primary_contact_name = contact_name
                fields_to_update.append("primary_contact_name")

            if not company.primary_contact_email and contact_email:
                company.primary_contact_email = contact_email
                fields_to_update.append("primary_contact_email")

            if not company.phone and self.phone:
                company.phone = self.phone
                fields_to_update.append("phone")

            if not company.website and self.website_url:
                company.website = self.website_url
                fields_to_update.append("website")

            if not company.consultation_sheet_url and self.sheet_url:
                company.consultation_sheet_url = self.sheet_url
                fields_to_update.append("consultation_sheet_url")

            if fields_to_update:
                company.save(update_fields=fields_to_update)

        return company

    # -------------------------------------------------------------------
    # Helper: mark deposit paid + create PortalInvite
    # -------------------------------------------------------------------

    @transaction.atomic
    def mark_deposit_paid_and_invite(self, *, expires_days=7, actor=None):

        from companyApp.models import PortalInvite

        # Update prospect status
        if self.status != self.Status.DEPOSIT_PAID:
            self.status = self.Status.DEPOSIT_PAID
            self.updated_by = actor
            self.save(update_fields=["status", "updated_by", "updated_at"])

        company = self.create_or_update_company(actor=actor)

        invite = PortalInvite.objects.create(
            company=company,
            email=self.email,
            expires_at=timezone.now() + timedelta(days=expires_days),
        )

        # Actual email send will be handled in a view, signal, or admin action.
        return company, invite


# =======================================================================
#                            PROSPECT NOTES
# =======================================================================

class ProspectNote(models.Model):
    prospect = models.ForeignKey(
        Prospect,
        on_delete=models.CASCADE,
        related_name="notes_log",
    )
    subject = models.CharField(max_length=160, blank=True)
    body_md = models.TextField(blank=True)
    is_pinned = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prospect_notes_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_pinned", "-created_at", "pk")

    def __str__(self):
        return self.subject or f"Note #{self.pk}"
