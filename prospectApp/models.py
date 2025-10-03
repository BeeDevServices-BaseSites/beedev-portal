from django.db import models
from django.conf import settings
from django.core.validators import URLValidator
from django.utils import timezone
import secrets
from django.db import transaction
from companyApp.models import Company, CompanyContact

def _coalesce(*vals):
    for v in vals:
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Prospect(TimeStamped):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        RESEARCHED = "RES", "Researched"
        READY = "RDY", "Ready to Contact"
        EMAILED = "EML", "Emailed"
        REPLIED = "RPL", "Replied"
        BOUNCED = "BNC", "Bounced"
        UNSUB = "UNS", "Unsubscribed"
        WON = "WON", "Converted"
        LOST = "LST", "Not a Fit"

    full_name   = models.CharField(max_length=120, blank=True)
    company_name= models.CharField(max_length=160, blank=True)
    email       = models.EmailField(unique=True)
    phone       = models.CharField(max_length=40, blank=True)

    address1    = models.CharField(max_length=160, blank=True)
    address2    = models.CharField(max_length=160, blank=True)
    city        = models.CharField(max_length=80,  blank=True)
    state       = models.CharField(max_length=80,  blank=True)
    postal_code = models.CharField(max_length=20,  blank=True)
    country     = models.CharField(max_length=60,  blank=True, default="USA")

    website_url = models.CharField(max_length=300, blank=True, validators=[URLValidator()], help_text="Leave blank if no site")
    notes       = models.TextField(blank=True)

    status      = models.CharField(max_length=3, choices=Status.choices, default=Status.NEW)
    tags        = models.CharField(max_length=200, blank=True, help_text="Comma-separated")

    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="prospects_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="prospects_updated")

    do_not_contact = models.BooleanField(default=False)
    unsubscribe_token = models.CharField(max_length=32, unique=True, editable=False, blank=True)

    company = models.ForeignKey(
        Company, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="prospects"
    )

    def save(self, *args, **kwargs):
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_hex(16)
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def onboarded(self) -> bool:
        return bool(self.company_id and self.company.has_client_users)

    @property
    def has_website(self): 
        return bool(self.website_url)

    def __str__(self):
        base = self.company_name or self.full_name or self.email
        return f"{base} ({self.email})"

    @transaction.atomic
    def convert_to_company(self, *, actor=None, update_if_exists=True):
        company_name = _coalesce(
            getattr(self, "company_name", None),
            getattr(self, "name", None),
        ) or "Unnamed Company"

        contact_name = _coalesce(
            getattr(self, "primary_contact_name", None),
            getattr(self, "contact_name", None),
            getattr(self, "full_name", None),
            f"{getattr(self, 'first_name', '')} {getattr(self, 'last_name', '')}",
        )

        contact_email = _coalesce(
            getattr(self, "primary_email", None),
            getattr(self, "contact_email", None),
            getattr(self, "email", None),
        ).lower()

        company, created = Company.objects.get_or_create(
            name=company_name,
            defaults={
                "primary_contact_name": contact_name,
                "primary_email": contact_email,
                "phone": getattr(self, "phone", "") or "",
                "website": getattr(self, "website_url", "") or "",
                "status": Company.Status.CONVERTED_PROSPECT,
            },
        )

        if not created and update_if_exists:
            fields_to_update = []
            if contact_name and not company.primary_contact_name:
                company.primary_contact_name = contact_name
                fields_to_update.append("primary_contact_name")
            if contact_email and not company.primary_email:
                company.primary_email = contact_email
                fields_to_update.append("primary_email")
            if fields_to_update:
                company.save(update_fields=fields_to_update)

        if contact_email:
            CompanyContact.objects.get_or_create(
                company=company,
                email=contact_email,
                defaults={
                    "name": contact_name or "",
                    "title": getattr(self, "title", "") or "",
                    "phone": getattr(self, "phone", "") or "",
                    "is_primary": True,
                },
            )
        updates = []
        if not self.company_id:
            self.company = company
            updates.append("company")
        if self.status != self.Status.WON:
            self.status = self.Status.WON
            updates.append("status")
        if updates:
            self.save(update_fields=updates)

        return company
    
class ProspectNote(models.Model):
    prospect    = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="notes_log")
    subject     = models.CharField(max_length=160, blank=True)
    body_md     = models.TextField(blank=True)
    is_pinned   = models.BooleanField(default=False)

    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="prospect_notes_created"
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_pinned", "-created_at", "pk")

    def __str__(self):
        return self.subject or f"Note #{self.pk}"