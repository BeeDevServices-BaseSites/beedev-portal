# userApp/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import User, ClientProfile, EmployeeProfile, StaffDocument


# -------------------------------------------------------------------
# Helpers based on your User.role
# -------------------------------------------------------------------

def is_owner(user: User) -> bool:
    return user.is_active and (user.is_superuser or user.role == User.Roles.OWNER)


def is_staff_role(user: User) -> bool:
    return user.is_active and user.role == User.Roles.STAFF


def is_client_role(user: User) -> bool:
    return user.is_active and user.role == User.Roles.CLIENT


# -------------------------------------------------------------------
# Inlines
# -------------------------------------------------------------------

class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    fk_name = "user"
    can_delete = False
    extra = 0
    max_num = 1
    readonly_fields = ("image_preview",)

    fields = (
        "profile_image", "image_preview",
        "company_name", "company_email", "phone",
        "address_line1", "address_line2", "city",
        "state_region", "postal_code", "country",
    )

    def image_preview(self, obj):
        if obj and obj.profile_image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.profile_image.url,
            )
        return "—"

    image_preview.short_description = "Preview"


class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    fk_name = "user"
    can_delete = False
    extra = 0
    max_num = 1
    readonly_fields = ("image_preview",)

    fields = (
        "profile_image", "image_preview",
        "job_title", "work_email", "work_phone", "discord_handle",
        "address_line1", "address_line2", "city",
        "state_region", "postal_code", "country",
        "notes_internal",
    )

    def image_preview(self, obj):
        if obj and obj.profile_image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.profile_image.url,
            )
        return "—"

    image_preview.short_description = "Preview"


# -------------------------------------------------------------------
# User admin
# -------------------------------------------------------------------

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
        "is_superuser",
        "is_active",
        "last_login",
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    inlines = []

    # ---- Permissions on the module itself ----

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return is_owner(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)

    def has_change_permission(self, request, obj=None):
        user = request.user

        if not user.is_staff:
            return False

        if is_owner(user):
            return True

        if is_staff_role(user):
            if obj is None:
                return True
            return obj.pk == user.pk

        return False

    # ---- Queryset restriction ----

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if is_owner(user):
            return qs

        if is_staff_role(user):
            return qs.filter(pk=user.pk)

        return qs.none()

    # ---- Readonly fields per role ----

    def get_readonly_fields(self, request, obj=None):
        ro = set(super().get_readonly_fields(request, obj))
        user = request.user

        if not is_owner(user):
            ro.update(
                {
                    "is_superuser",
                    "is_staff",
                    "groups",
                    "user_permissions",
                    "last_login",
                    "date_joined",
                }
            )

        if is_staff_role(user):
            ro.update({"username", "email", "role", "is_active"})

        return tuple(ro)

    # ---- Fieldsets (what fields show up on the form) ----

    def get_fieldsets(self, request, obj=None):
        user = request.user

        if is_owner(user):
            base = list(super().get_fieldsets(request, obj))
            base.append(
                (
                    _("Role"),
                    {
                        "fields": ("role",),
                    },
                )
            )
            return tuple(base)

        return (
            (None, {"fields": ("username", "password")}),
            (
                _("Personal info"),
                {
                    "fields": ("first_name", "last_name", "email"),
                },
            ),
            (
                _("Status"),
                {
                    "fields": ("is_active",),
                },
            ),
        )

    # ---- Inlines per user and viewer ----

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []

        inlines = []

        if obj.role == User.Roles.CLIENT:
            inlines.append(ClientProfileInline(self.model, self.admin_site))

        if obj.role in (User.Roles.STAFF, User.Roles.OWNER):
            inlines.append(EmployeeProfileInline(self.model, self.admin_site))

        return inlines


# -------------------------------------------------------------------
# ClientProfile admin
# -------------------------------------------------------------------

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "phone", "city", "state_region", "updated_at")
    search_fields = (
        "user__username",
        "user__email",
        "company_name",
        "phone",
        "city",
        "state_region",
        "postal_code",
    )
    autocomplete_fields = ["user"]
    readonly_fields = ("image_preview", "created_at", "updated_at")

    fields = (
        "user",
        "profile_image",
        "image_preview",
        "company_name",
        "company_email",
        "phone",
        "address_line1",
        "address_line2",
        "city",
        "state_region",
        "postal_code",
        "country",
        "created_at",
        "updated_at",
    )

    def image_preview(self, obj):
        if obj and obj.profile_image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.profile_image.url,
            )
        return "—"

    image_preview.short_description = "Preview"

    def has_module_permission(self, request):
        return request.user.is_staff


# -------------------------------------------------------------------
# EmployeeProfile admin
# -------------------------------------------------------------------

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title", "work_phone", "discord_handle", "updated_at")
    search_fields = (
        "user__username",
        "user__email",
        "job_title",
        "work_phone",
        "discord_handle",
    )
    autocomplete_fields = ["user"]
    readonly_fields = ("image_preview", "created_at", "updated_at")

    fields = (
        "user",
        "profile_image",
        "image_preview",
        "job_title",
        "work_email",
        "work_phone",
        "discord_handle",
        "address_line1",
        "address_line2",
        "city",
        "state_region",
        "postal_code",
        "country",
        "notes_internal",
        "created_at",
        "updated_at",
    )

    def image_preview(self, obj):
        if obj and obj.profile_image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.profile_image.url,
            )
        return "—"

    image_preview.short_description = "Preview"

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return is_owner(request.user)

    def has_change_permission(self, request, obj=None):
        user = request.user
        if is_owner(user):
            return True
        if is_staff_role(user):
            if obj is None:
                return True
            return obj.user_id == user.id
        return False

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)


# -------------------------------------------------------------------
# StaffDocument admin (contracts & payout sheets)
# -------------------------------------------------------------------

@admin.register(StaffDocument)
class StaffDocumentAdmin(admin.ModelAdmin):
    list_display = ("user", "doc_type", "title", "year", "month", "created_at")
    list_filter = ("doc_type", "year")
    search_fields = ("title", "user__username", "user__email")
    autocomplete_fields = ("user",)

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_add_permission(self, request):
        return is_owner(request.user)

    def has_change_permission(self, request, obj=None):
        user = request.user
        if is_owner(user):
            return True
        if is_staff_role(user):
            if obj is None:
                return True
            return obj.user_id == user.id
        return False

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)
