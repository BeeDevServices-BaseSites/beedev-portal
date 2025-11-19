# userApp/models.py
import os
import uuid
import datetime
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.templatetags.static import static

# ---------- Image helpers ----------

ALLOWED_IMAGE_EXTS = ["jpg", "jpeg", "png", "webp"]
MAX_IMAGE_BYTES = 3 * 1024 * 1024  # 3 MB

def validate_image_size(f):
    if f.size and f.size > MAX_IMAGE_BYTES:
        raise ValidationError(f"Image too large (>{MAX_IMAGE_BYTES // 1024 // 1024}MB).")

def avatar_upload_to(instance, filename):
    """
    Store at: media/profiles/YYYY/MM/<userId>-<uuid>.<ext>
    """
    ext = os.path.splitext(filename)[1].lower().lstrip(".") or "jpg"
    if ext not in ALLOWED_IMAGE_EXTS:
        ext = "jpg"
    today = datetime.date.today()
    user_id = getattr(instance.user, "id", "anon")
    return f"profiles/{today.year}/{today.month:02d}/{user_id}-{uuid.uuid4().hex}.{ext}"


# ---------- Staff document helpers (contracts & payout statements) ----------

ALLOWED_DOC_EXTS = ["pdf", "jpg", "jpeg", "png", "webp", "doc", "docx", "xls", "xlsx"]
MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB

def validate_doc_size(f):
    if f.size and f.size > MAX_DOC_BYTES:
        raise ValidationError(f"File too large (>{MAX_DOC_BYTES // 1024 // 1024}MB).")

def staff_document_upload_to(instance, filename):
    """
    Store staff docs at:
      media/staff-docs/<userId>/<doctype>/<uuid>.<ext>
    """
    ext = os.path.splitext(filename)[1].lower().lstrip(".") or "pdf"
    if ext not in ALLOWED_DOC_EXTS:
        ext = "pdf"
    user_id = instance.user_id or "staff"
    doctype = instance.doc_type or "other"
    return f"staff-docs/{user_id}/{doctype}/{uuid.uuid4().hex}.{ext}"


# =======================================================================
#                               USER
# =======================================================================

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Roles.OWNER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    class Roles(models.TextChoices):
        OWNER = "OWNER", "Owner"
        STAFF = "STAFF", "Staff"
        CLIENT = "CLIENT", "Client"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CLIENT,
    )

    objects = CustomUserManager()

    def __str__(self):
        return self.username or self.email

    # -------- Convenience role helpers (nice for views & templates) --------
    @property
    def is_owner_role(self) -> bool:
        return self.role == self.Roles.OWNER

    @property
    def is_staff_role(self) -> bool:
        return self.role in {self.Roles.STAFF, self.Roles.OWNER}

    @property
    def is_client_role(self) -> bool:
        return self.role == self.Roles.CLIENT

    @property
    def preferred_name(self) -> str:
        return (self.first_name or "").strip() or self.username or self.email

    @property
    def display_name(self) -> str:
        full = f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()
        return full or self.username or self.email

    def fullName(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def avatar_url(self) -> str:
        try:
            ep = getattr(self, "employee_profile", None)
            if ep and ep.profile_image:
                return ep.profile_image.url
        except Exception:
            pass

        try:
            cp = getattr(self, "profile", None)
            if cp and cp.profile_image:
                return cp.profile_image.url
        except Exception:
            pass

        return static("images/beehive.jpeg")


# =======================================================================
#                             CLIENT PROFILE
# =======================================================================

class ClientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    profile_image = models.ImageField(
        upload_to=avatar_upload_to,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(ALLOWED_IMAGE_EXTS), validate_image_size],
        help_text="JPEG/PNG/WebP, up to 3MB.",
    )

    company_name = models.CharField(max_length=200, blank=True)
    company_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state_region = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=120, blank=True, default="USA")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ClientProfile({self.user.username or self.user.email})"


# =======================================================================
#                           EMPLOYEE PROFILE
# =======================================================================

class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )

    profile_image = models.ImageField(
        upload_to=avatar_upload_to,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(ALLOWED_IMAGE_EXTS), validate_image_size],
        help_text="JPEG/PNG/WebP, up to 3MB.",
    )

    job_title = models.CharField(max_length=120, blank=True)
    work_email = models.EmailField(blank=True)
    work_phone = models.CharField(max_length=30, blank=True)
    discord_handle = models.CharField(max_length=60, blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state_region = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=120, blank=True, default="USA")

    notes_internal = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"EmployeeProfile({self.user.username or self.user.email})"


# =======================================================================
#                           STAFF DOCUMENTS
# =======================================================================

class StaffDocument(models.Model):
    class DocType(models.TextChoices):
        CONTRACT         = "contract", "Contract"
        PAYOUT_STATEMENT = "payout_statement", "Payout Statement"
        OTHER            = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_documents",
    )

    doc_type = models.CharField(
        max_length=40,
        choices=DocType.choices,
        default=DocType.OTHER,
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Either an uploaded file, or an external URL (e.g. Google Sheet),
    # or both if you want.
    file = models.FileField(
        upload_to=staff_document_upload_to,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(ALLOWED_DOC_EXTS),
            validate_doc_size,
        ],
        help_text="PDF or image files up to 10MB.",
    )

    external_url = models.URLField(
        blank=True,
        help_text="Optional external URL (e.g. Google Sheet for payouts).",
    )

    year  = models.PositiveIntegerField(blank=True, null=True)
    month = models.PositiveSmallIntegerField(blank=True, null=True, help_text="1–12 if applicable")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.title} ({self.doc_type})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.file and not self.external_url:
            raise ValidationError("Provide either an uploaded file or an external URL.")