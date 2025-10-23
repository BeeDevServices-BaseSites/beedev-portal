from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class TimeEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="time_entries"
    )
    project = models.ForeignKey(
        "projectApp.Project", on_delete=models.CASCADE, related_name="time_entries"
    )
    job_rate = models.ForeignKey(
        "proposalApp.JobRate", on_delete=models.PROTECT, related_name="time_entries"
    )

    notes = models.CharField(max_length=240, blank=True)

    start_at = models.DateTimeField()
    end_at   = models.DateTimeField(null=True, blank=True)
    duration_secs = models.PositiveIntegerField(default=0)

    billable = models.BooleanField(default=True)
    tags = models.JSONField(null=True, blank=True)

    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="time_approved"
    )

    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="time_locked"
    )

    invoice = models.ForeignKey(
        "invoiceApp.Invoice", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="time_entries"
    )

    payroll_batch = models.ForeignKey(
        "timeApp.PayrollBatch", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="entries"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_at", "id")
        indexes = [
            models.Index(fields=["project", "user", "start_at"]),
            models.Index(fields=["approved_at"]),
            models.Index(fields=["invoice"]),
        ]

    def __str__(self):
        return f"{self.user} · {self.project} · {self.start_at:%Y-%m-%d %H:%M}"

    @property
    def hours(self) -> Decimal:
        return (Decimal(self.duration_secs or 0) / Decimal(3600)).quantize(Decimal("0.01"))

    def finalize_duration(self):
        if self.end_at and self.start_at:
            delta = (self.end_at - self.start_at).total_seconds()
            self.duration_secs = max(0, int(delta))

    def approve(self, *, actor=None, at=None, save=True):
        if not self.approved_at:
            self.approved_at = at or timezone.now()
            if actor:
                self.approved_by = actor
            if save:
                self.save(update_fields=["approved_at", "approved_by", "updated_at"])

    def lock(self, *, actor=None, at=None, save=True):
        if not self.locked_at:
            self.locked_at = at or timezone.now()
            if actor:
                self.locked_by = actor
            if save:
                self.save(update_fields=["locked_at", "locked_by", "updated_at"])

    def unlock(self, *, save=True):
        self.locked_at = None
        self.locked_by = None
        if save:
            self.save(update_fields=["locked_at", "locked_by", "updated_at"])

    def clean(self):
        if self.end_at and self.start_at and self.end_at < self.start_at:
            from django.core.exceptions import ValidationError
            raise ValidationError({"end_at": "End time must be after start time."})

    def save(self, *args, **kwargs):
        if self.end_at and self.start_at:
            self.finalize_duration()
        super().save(*args, **kwargs)

class ActiveTimer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="active_timer"
    )
    project = models.ForeignKey("projectApp.Project", on_delete=models.CASCADE)
    job_rate = models.ForeignKey("proposalApp.JobRate", on_delete=models.PROTECT)
    notes = models.CharField(max_length=240, blank=True)
    started_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Timer · {self.user} · {self.project} · {self.started_at:%Y-%m-%d %H:%M}"

    @transaction.atomic
    def stop_and_create_entry(self, *, billable=True) -> TimeEntry:
        end = timezone.now()
        entry = TimeEntry.objects.create(
            user=self.user,
            project=self.project,
            job_rate=self.job_rate,
            notes=self.notes,
            start_at=self.started_at,
            end_at=end,
            billable=billable,
        )
        entry.finalize_duration()
        entry.save(update_fields=["duration_secs", "updated_at"])
        self.delete()
        return entry

class PayrollBatch(models.Model):
    PERIOD_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("BIWEEKLY", "Bi-Weekly"),
        ("SEMI", "Semi-Monthly"),
        ("MONTHLY", "Monthly"),
        ("CUSTOM", "Custom"),
    ]
    name = models.CharField(max_length=120)
    period = models.CharField(max_length=12, choices=PERIOD_CHOICES, default="BIWEEKLY")
    start_date = models.DateField()
    end_date = models.DateField()
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payroll_finalized"
    )
    notes = models.CharField(max_length=240, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_date", "id")

    def __str__(self):
        return f"{self.name} ({self.start_date} → {self.end_date})"

    @property
    def is_finalized(self) -> bool:
        return bool(self.finalized_at)

    def finalize(self, *, actor=None, at=None, save=True):
        if not self.finalized_at:
            self.finalized_at = at or timezone.now()
            if actor:
                self.finalized_by = actor
            if save:
                self.save(update_fields=["finalized_at", "finalized_by", "updated_at"])