# timeApp/admin.py
from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from .models import TimeEntry, ActiveTimer, PayrollBatch

# -------- Helpers
def _sum_hours(queryset):
    secs = queryset.aggregate(s=Sum("duration_secs")).get("s") or 0
    return (Decimal(secs) / Decimal(3600)).quantize(Decimal("0.01"))

# -------- TimeEntry admin
@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "project", "job_rate", "start_at", "end_at",
        "hours", "billable", "approved_at", "locked_at", "invoice", "payroll_batch",
    )
    list_filter = (
        "billable", "approved_at", "locked_at", "job_rate", "project", "payroll_batch",
    )
    search_fields = ("notes", "user__email", "user__username", "project__name")
    readonly_fields = ("created_at", "updated_at", "duration_secs",)
    autocomplete_fields = ("user", "project", "job_rate", "invoice", "payroll_batch")
    date_hierarchy = "start_at"
    actions = [
        "approve_entries",
        "lock_entries",
        "unlock_entries",
        "clear_invoice_link",
        "add_to_new_payroll_batch",
        "remove_from_payroll_batch",
    ]

    # Existing approval/lock actions
    def approve_entries(self, request, queryset):
        n = 0
        for t in queryset:
            t.approve(actor=request.user, save=True)
            n += 1
        self.message_user(request, f"Approved {n} entries.")
    approve_entries.short_description = "Approve selected entries"

    def lock_entries(self, request, queryset):
        n = 0
        for t in queryset:
            t.lock(actor=request.user, save=True)
            n += 1
        self.message_user(request, f"Locked {n} entries.")
    lock_entries.short_description = "Lock selected entries"

    def unlock_entries(self, request, queryset):
        n = 0
        for t in queryset:
            t.unlock(save=True)
            n += 1
        self.message_user(request, f"Unlocked {n} entries.")
    unlock_entries.short_description = "Unlock selected entries"

    def clear_invoice_link(self, request, queryset):
        n = queryset.update(invoice=None)
        self.message_user(request, f"Cleared invoice link on {n} entries.")
    clear_invoice_link.short_description = "Clear invoice link"

    # New payroll actions
    def add_to_new_payroll_batch(self, request, queryset):
        """
        Creates a new PayrollBatch covering the min/max dates of selected entries,
        assigns entries to it, and locks them.
        """
        if not queryset.exists():
            self.message_user(request, "No entries selected.", level="warning")
            return

        # Determine range from selected entries
        first_start = queryset.order_by("start_at").first().start_at.date()
        last_end = (queryset.order_by("-end_at").first().end_at or timezone.now()).date()

        # Batch name like "Payroll 2025-10-01–2025-10-15"
        name = f"Payroll {first_start}–{last_end}"
        batch = PayrollBatch.objects.create(
            name=name,
            period="CUSTOM",
            start_date=first_start,
            end_date=last_end,
        )

        # Assign + lock
        updated = queryset.update(payroll_batch=batch)
        for t in queryset:
            t.lock(actor=request.user, save=True)

        total_hours = _sum_hours(queryset)
        self.message_user(
            request,
            f"Created batch '{batch.name}' and assigned {updated} entries "
            f"(total {total_hours} hrs). Entries locked."
        )
    add_to_new_payroll_batch.short_description = "Create payroll batch from selection (assign + lock)"

    def remove_from_payroll_batch(self, request, queryset):
        """
        Clears payroll_batch and unlocks the entries.
        """
        n = 0
        for t in queryset:
            if t.payroll_batch_id:
                t.payroll_batch = None
                t.unlock(save=True)
                t.save(update_fields=["payroll_batch", "updated_at"])
                n += 1
        self.message_user(request, f"Removed {n} entries from payroll batches and unlocked them.")
    remove_from_payroll_batch.short_description = "Remove from payroll batch (and unlock)"

# -------- ActiveTimer admin
@admin.register(ActiveTimer)
class ActiveTimerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "project", "job_rate", "started_at")
    autocomplete_fields = ("user", "project", "job_rate")
    search_fields = ("user__email", "user__username", "project__name")
    date_hierarchy = "started_at"

# -------- PayrollBatch admin
@admin.register(PayrollBatch)
class PayrollBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "period", "start_date", "end_date",
        "entries_count", "total_hours", "finalized_at", "finalized_by",
    )
    list_filter = ("period", "finalized_at",)
    search_fields = ("name", "notes")
    readonly_fields = ("created_at", "updated_at",)
    actions = ["finalize_batches", "reopen_batches"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # annotate with totals efficiently if needed; keeping simple aggregation methods here
        return qs

    def entries_count(self, obj):
        return obj.entries.count()
    entries_count.short_description = "Entries"

    def total_hours(self, obj):
        return _sum_hours(obj.entries.all())
    total_hours.short_description = "Hours"

    def finalize_batches(self, request, queryset):
        n = 0
        for b in queryset:
            if not b.is_finalized:
                b.finalize(actor=request.user, save=True)
                n += 1
        self.message_user(request, f"Finalized {n} payroll batch(es).")
    finalize_batches.short_description = "Finalize selected batches"

    def reopen_batches(self, request, queryset):
        n = 0
        for b in queryset:
            if b.is_finalized:
                b.finalized_at = None
                b.finalized_by = None
                b.save(update_fields=["finalized_at", "finalized_by", "updated_at"])
                n += 1
        self.message_user(request, f"Reopened {n} payroll batch(es).")
    reopen_batches.short_description = "Reopen selected batches"
