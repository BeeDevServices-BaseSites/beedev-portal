# onboardingApp/admin.py

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    OnboardingTaskTemplate,
    OnboardingList,
    OnboardingListItem,
)

# ---------- permission helpers (match your other apps) ----------

def is_owner(u):
    return u.is_active and (u.is_superuser or u.groups.filter(name="Owner").exists())


def is_admin(u):
    return u.is_active and u.groups.filter(name="Admin").exists()


def is_hr(u):
    return u.is_active and u.groups.filter(name="HR").exists()


def is_plain_staff(u):
    return u.is_active and u.is_staff and not is_owner(u) and not is_admin(u) and not is_hr(u)


# ============================ Inlines ============================

class OnboardingListItemInline(admin.TabularInline):
    """
    Inline for items inside a single onboarding list.
    You can tweak which fields are editable vs read-only.
    """
    model = OnboardingListItem
    extra = 0
    autocomplete_fields = ("completed_by",)
    fields = (
        "title",
        "is_completed",
        "completed_by",
        "resource_url",
        "sort_order",
        "notes",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user) or is_hr(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)


# ============================ Task Templates ============================

@admin.register(OnboardingTaskTemplate)
class OnboardingTaskTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "audience",
        "default_order",
        "is_active",
        "updated_at",
    )
    list_filter = ("audience", "is_active")
    search_fields = ("code", "title", "description")
    ordering = ("audience", "default_order", "title")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "code",
        "audience",
        "title",
        "description",
        "default_order",
        "is_active",
        "created_at",
        "updated_at",
    )

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_add_permission(self, request):
        return is_owner(request.user) or is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)


# ============================ Onboarding Lists ============================

@admin.register(OnboardingList)
class OnboardingListAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "kind",
        "subject_label",
        "visible_to_subject",
        "management_only",
        "is_archived",
        "created_at",
        "completed_at",
    )
    list_filter = (
        "kind",
        "visible_to_subject",
        "management_only",
        "is_archived",
    )
    search_fields = (
        "title",
        "notes",
        "staff_user__username",
        "staff_user__email",
        "company__name",
    )
    autocomplete_fields = (
        "staff_user",
        "company",
        "created_for",
    )
    inlines = [OnboardingListItemInline]

    readonly_fields = ("created_at", "updated_at")
    fields = (
        "kind",
        "staff_user",
        "company",
        "title",
        "notes",
        "created_for",
        "visible_to_subject",
        "management_only",
        "completed_at",
        "is_archived",
        "created_at",
        "updated_at",
    )

    def display_name(self, obj):
        return str(obj)
    display_name.short_description = "Onboarding List"

    def subject_label(self, obj):
        if obj.kind == obj.Kind.STAFF and obj.staff_user:
            return obj.staff_user.get_username() if hasattr(obj.staff_user, "get_username") else obj.staff_user
        if obj.kind == obj.Kind.CLIENT and obj.company:
            return obj.company.name
        return "—"
    subject_label.short_description = "Subject"

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_add_permission(self, request):
        return is_owner(request.user) or is_admin(request.user) or is_hr(request.user)

    def has_change_permission(self, request, obj=None):
        if is_owner(request.user) or is_admin(request.user):
            return True
        if is_hr(request.user):
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.pk:
            obj.populate_from_templates()


# ============================ Onboarding Items ============================

@admin.register(OnboardingListItem)
class OnboardingListItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "onboarding_list",
        "is_completed",
        "completed_at",
        "completed_by",
        "sort_order",
    )
    list_filter = ("is_completed", "onboarding_list__kind")
    search_fields = (
        "title",
        "description",
        "notes",
        "onboarding_list__title",
        "onboarding_list__staff_user__username",
        "onboarding_list__company__name",
    )
    autocomplete_fields = ("onboarding_list", "template", "completed_by")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "onboarding_list",
        "template",
        "title",
        "description",
        "sort_order",
        "is_completed",
        "completed_at",
        "completed_by",
        "resource_url",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_add_permission(self, request):
        # Usually created via populate_from_templates, but allow Owner/Admin to add manually
        return is_owner(request.user) or is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        # Owner/Admin/HR can edit; you could also allow plain staff to tick checkboxes here if you want
        return is_owner(request.user) or is_admin(request.user) or is_hr(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user) or is_admin(request.user)
