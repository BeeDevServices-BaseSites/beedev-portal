# onboardingApp/models.py

from django.db import models, transaction
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


# =======================================================================
#                            BASE TIMESTAMPED
# =======================================================================

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# =======================================================================
#                       TASK TEMPLATES (MASTER LIST)
# =======================================================================

class OnboardingTaskTemplate(TimeStamped):
    class Audience(models.TextChoices):
        STAFF = "STAFF", "Staff"
        CLIENT = "CLIENT", "Client"

    code = models.SlugField(
        max_length=80,
        unique=True,
        help_text="Short code, e.g. 'staff-welcome-email'.",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    audience = models.CharField(
        max_length=12,
        choices=Audience.choices,
        help_text="Whether this task is used for staff or client onboarding.",
    )

    default_order = models.PositiveIntegerField(
        default=100,
        help_text="Smaller numbers appear earlier in the checklist.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Inactive templates won't be added to new onboarding lists.",
    )

    class Meta:
        ordering = ("audience", "default_order", "title")

    def __str__(self):
        return f"{self.get_audience_display()} · {self.title}"


# =======================================================================
#                           ONBOARDING LIST
# =======================================================================

class OnboardingList(TimeStamped):
    class Kind(models.TextChoices):
        STAFF = "STAFF", "Staff Onboarding"
        CLIENT = "CLIENT", "Client Onboarding"

    kind = models.CharField(
        max_length=12,
        choices=Kind.choices,
    )

    staff_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="staff_onboarding_lists",
        help_text="Set for staff/intern onboarding.",
    )
    company = models.ForeignKey(
        "companyApp.Company",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="client_onboarding_lists",
        help_text="Set for client onboarding.",
    )

    title = models.CharField(
        max_length=200,
        help_text="Friendly label, e.g. 'Staff Onboarding – Jane Doe'.",
    )
    notes = models.TextField(blank=True)

    created_for = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="onboarding_lists_created",
        help_text="Who created this list (usually a manager/owner).",
    )

    visible_to_subject = models.BooleanField(
        default=False,
        help_text="If true: staff_user/client will see this checklist in their portal.",
    )
    management_only = models.BooleanField(
        default=False,
        help_text="If true: only management-level staff should see in UI.",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional: when the ENTIRE list was completed.",
    )
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at", "pk")

    def __str__(self):
        if self.kind == self.Kind.STAFF and self.staff_user:
            return f"Staff Onboarding – {self.staff_user}"
        if self.kind == self.Kind.CLIENT and self.company:
            return f"Client Onboarding – {self.company}"
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.kind == self.Kind.STAFF and not self.staff_user:
            raise ValidationError({"staff_user": "Staff onboarding list must have a staff_user."})
        if self.kind == self.Kind.CLIENT and not self.company:
            raise ValidationError({"company": "Client onboarding list must have a company."})

    @transaction.atomic
    def populate_from_templates(self):
        audience = (
            OnboardingTaskTemplate.Audience.STAFF
            if self.kind == self.Kind.STAFF
            else OnboardingTaskTemplate.Audience.CLIENT
        )

        templates = OnboardingTaskTemplate.objects.filter(
            audience=audience,
            is_active=True,
        ).order_by("default_order", "title")

        items = []
        for tmpl in templates:
            items.append(
                OnboardingListItem(
                    onboarding_list=self,
                    template=tmpl,
                    title=tmpl.title,
                    description=tmpl.description,
                    sort_order=tmpl.default_order,
                )
            )
        OnboardingListItem.objects.bulk_create(items)
    
    @property
    def total_items(self) -> int:
        return self.items.count()

    @property
    def completed_items(self) -> int:
        return self.items.filter(is_completed=True).count()

    @property
    def percent_complete(self) -> int:
        total = self.total_items
        if not total:
            return 0
        return round(self.completed_items * 100 / total)
    
    def refresh_completion_status(self, save=True):
        total = self.items.count()
        done = self.items.filter(is_completed=True).count()

        if total > 0 and done == total and self.completed_at is None:
            self.completed_at = timezone.now()
            if save:
                self.save(update_fields=["completed_at", "updated_at"])
        elif done < total and self.completed_at is not None:
            self.completed_at = None
            if save:
                self.save(update_fields=["completed_at", "updated_at"])


# =======================================================================
#                         ONBOARDING LIST ITEMS
# =======================================================================

class OnboardingListItem(TimeStamped):
    onboarding_list = models.ForeignKey(
        OnboardingList,
        on_delete=models.CASCADE,
        related_name="items",
    )
    template = models.ForeignKey(
        OnboardingTaskTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="list_items",
        help_text="Optional link back to the template this was created from.",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    sort_order = models.PositiveIntegerField(default=100)

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="onboarding_items_completed",
    )

    resource_url = models.URLField(
        blank=True,
        help_text="Optional link relevant to this task (contract, preview site, folder, etc.).",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"{self.onboarding_list} · {self.title}"

    def mark_complete(self, user=None):
        self.is_completed = True
        self.completed_at = timezone.now()
        if user:
            self.completed_by = user
        self.save(update_fields=["is_completed", "completed_at", "completed_by", "updated_at"])

        self.onboarding_list.refresh_completion_status(save=True)
