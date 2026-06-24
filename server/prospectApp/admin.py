# prospectApp/admin.py

from django.contrib import admin, messages
from django.db import transaction

from .models import Prospect, ProspectNote


# =======================================================================
#                         ADMIN ACTIONS
# =======================================================================

@admin.action(description="Convert to Company (mark as WON)")
def convert_to_company(modeladmin, request, queryset):
    success_count = 0
    error_count = 0

    with transaction.atomic():
        for prospect in queryset.select_for_update():
            try:
                company = prospect.create_or_update_company(actor=request.user)

                if hasattr(Prospect.Status, "WON"):
                    if prospect.status != Prospect.Status.WON:
                        prospect.status = Prospect.Status.WON
                        prospect.updated_by = request.user
                        prospect.save(update_fields=["status", "updated_by", "updated_at"])

                success_count += 1

            except Exception as e:
                error_count += 1
                messages.error(
                    request,
                    f"Error converting prospect {prospect.email or prospect.pk}: {e}",
                )

    msg = f"Prospects processed: {success_count}."
    if error_count:
        msg += f" {error_count} failed."
    messages.success(request, msg)


# =======================================================================
#                         INLINES
# =======================================================================

class ProspectNoteInline(admin.TabularInline):
    model = ProspectNote
    extra = 0
    fields = ("subject", "body_md", "is_pinned", "created_by", "created_at")
    readonly_fields = ("created_by", "created_at")

    def save_new_objects(self, formset, commit=True):
        objs = super().save_new_objects(formset, commit=False)
        request = formset.request
        for obj in objs:
            if not obj.created_by:
                obj.created_by = request.user
        if commit:
            for obj in objs:
                obj.save()
        return objs


# =======================================================================
#                          PROSPECT ADMIN
# =======================================================================

@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "full_name",
        "email",
        "status",
        "has_website",
        "last_contacted_at",
        "next_follow_up_at",
        "country",
    )
    list_filter = ("status", "country")
    search_fields = (
        "company_name",
        "full_name",
        "email",
        "website_url",
        "tags",
        "notes",
        "city",
        "state",
    )

    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    fieldsets = (
        ("Prospect Info", {
            "fields": (
                "full_name",
                "company_name",
                "email",
                "phone",
                "website_url",
                "sheet_url",
                "status",
                "tags",
                "notes",
            )
        }),
        ("Address", {
            "fields": (
                "address1",
                "address2",
                "city",
                "state",
                "postal_code",
                "country",
            )
        }),
        ("Follow-up", {
            "fields": (
                "last_contacted_at",
                "next_follow_up_at",
            )
        }),
        ("Audit", {
            "fields": (
                "created_by",
                "updated_by",
                "created_at",
                "updated_at",
            )
        }),
    )

    inlines = [ProspectNoteInline]
    actions = [convert_to_company]

    # --- Make created_by / updated_by track who did what ---

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.request = request
        return formset
