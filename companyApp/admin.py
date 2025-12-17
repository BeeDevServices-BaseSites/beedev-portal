# companyApp/admin.py

from django import forms
from urllib.parse import urlparse, urlunparse

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.html import format_html

from .models import (
    Company,
    CompanyMember,
    ProposalDocument,
    RoadMap,
    Invoice,
    Agreement,
    CompanyUpdateLog,
    PortalInvite,
)

from userApp.models import User


# -------- permission helpers (Portal Lite) --------

def is_owner(user):
    return (
        user.is_active
        and (user.is_superuser or getattr(user, "role", None) == User.Roles.OWNER)
    )


def is_staff_role(user):
    return user.is_active and getattr(user, "role", None) == User.Roles.STAFF


# -------- Inlines --------

class CompanyMemberInline(admin.TabularInline):
    model = CompanyMember
    extra = 0
    autocomplete_fields = ("user",)
    fields = (
        "user",
        "member_type",
        "is_primary",
        "is_active",
        "added_at",
    )
    readonly_fields = ("added_at",)

    def has_add_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)

class ProposalDocumentInline(admin.TabularInline):
    model = ProposalDocument
    extra = 0
    fields = (
        "title",
        "version",
        "is_active",
        "visible_to_client",
        "file",
        "external_url",
        "created_by",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("created_by",)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

class RoadMapInline(admin.TabularInline):
    model = RoadMap
    extra = 0
    fields = (
        "title",
        "version",
        "is_active",
        "visible_to_client",
        "file",
        "external_url",
        "created_by",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("created_by",)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0
    fields = (
        "invoice_number",
        "title",
        "amount",
        "paid_at",
        "visible_to_client",
        "file",
        "external_url",
        "created_by",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("created_by",)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

class AgreementInline(admin.TabularInline):
    model = Agreement
    extra = 0
    fields = (
        "kind",
        "title",
        "status",
        "version",
        "file_signed",
        "file_source",
        "effective_date",
        "expires_at",
        "visible_to_client",
        "uploaded_by",
        "uploaded_at",
    )
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("uploaded_by",)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

class CompanyUpdateLogInline(admin.TabularInline):
    model = CompanyUpdateLog
    extra = 0
    fields = (
        "pinned",
        "title",
        "visible_to_client",
        "created_by",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("created_by",)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

class PortalInviteInline(admin.TabularInline):
    model = PortalInvite
    extra = 0
    fields = (
        "email",
        "created_at",
        "expires_at",
        "used",
    )
    readonly_fields = ("created_at", "expires_at", "used")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)


# -------- Company form (normalize website URL) --------

class CompanyAdminForm(forms.ModelForm):
    use_https = forms.BooleanField(
        required=False,
        initial=True,
        label="Use HTTPS for Website",
        help_text="If checked, the website will be stored with https://; "
                  "if unchecked, http://",
    )
    website = forms.CharField(required=False, label="Website")

    class Meta:
        model = Company
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.website:
            self.fields["use_https"].initial = (
                urlparse(self.instance.website).scheme == "https"
            )

    def clean(self):
        cleaned = super().clean()
        raw = (cleaned.get("website") or "").strip()
        use_https = bool(cleaned.get("use_https"))

        if not raw:
            cleaned["website"] = ""
            return cleaned

        scheme = "https" if use_https else "http"
        p = urlparse(raw)

        if not p.scheme:
            netloc, sep, path = raw.partition("/")
            if path and not path.startswith("/"):
                path = "/" + path
            final = f"{scheme}://{netloc}{path}"
        else:
            p = p._replace(scheme=scheme)
            final = urlunparse(p)

        try:
            URLValidator(schemes=["http", "https"])(final)
        except ValidationError as e:
            raise ValidationError({"website": e.messages})

        cleaned["website"] = final
        return cleaned


# -------- Company admin --------

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm

    list_display = (
        "logo_thumb",
        "name",
        "status",
        "pipeline_status",
        "work_status",
        "city",
        "state_region",
        "website",
        "updated_at",
    )
    list_filter = ("status", "pipeline_status", "work_status", "country")
    search_fields = (
        "name",
        "primary_contact_name",
        "primary_contact_email",
        "phone",
        "city",
        "state_region",
        "postal_code",
        "website",
    )
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [
        CompanyMemberInline,
        ProposalDocumentInline,
        RoadMapInline,
        AgreementInline,
        InvoiceInline,
        CompanyUpdateLogInline,
        PortalInviteInline,
    ]
    readonly_fields = ("logo_preview", "created_at", "updated_at")

    fieldsets = (
        ("Identity", {
            "fields": ("name", "slug", "status", "pipeline_status", "work_status"),
        }),
        ("Logo", {
            "fields": ("logo", "logo_preview", "logo_external_url"),
        }),
        ("Contact", {
            "fields": (
                "primary_contact_name",
                "primary_contact_email",
                "phone",
                "website",
                "use_https",
            ),
        }),
        ("Address", {
            "fields": (
                "address_line1",
                "address_line2",
                "city",
                "state_region",
                "postal_code",
                "country",
            ),
        }),
        ("Consultation / Prospect", {
            "fields": ("consultation_sheet_url", "prospect"),
        }),
        ("Audit", {
            "fields": ("created_by", "created_at", "updated_at"),
        }),
    )

    # ----- logo previews -----

    def logo_preview(self, obj):
        if obj and (obj.logo or obj.logo_external_url):
            url = obj.logo.url if obj.logo else obj.logo_external_url
            return format_html(
                '<img src="{}" style="height:48px;width:auto;'
                'object-fit:contain;border:1px solid #eee;padding:2px;background:#fff;" />',
                url,
            )
        return "—"

    logo_preview.short_description = "Logo"

    def logo_thumb(self, obj):
        if obj and (obj.logo or obj.logo_external_url):
            url = obj.logo.url if obj.logo else obj.logo_external_url
            return format_html(
                '<img src="{}" style="height:24px;width:auto;'
                'object-fit:contain;border:1px solid #eee;padding:1px;background:#fff;" />',
                url,
            )
        return "—"

    logo_thumb.short_description = ""

    # ----- permissions -----

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return is_owner(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return is_owner(request.user) or is_staff_role(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for obj in instances:
            if hasattr(obj, "created_by") and not obj.created_by:
                obj.created_by = request.user
            obj.save()

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()


# -------- Other model admins (lightweight) --------

@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "kind",
        "title",
        "status",
        "effective_date",
        "expires_at",
        "visible_to_client",
        "uploaded_at",
    )
    list_filter = ("kind", "status", "visible_to_client")
    search_fields = ("company__name", "title", "signed_by_name", "signed_by_email")
    autocomplete_fields = ("company", "uploaded_by")
    readonly_fields = ("uploaded_at", "updated_at")

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))

@admin.register(CompanyUpdateLog)
class CompanyUpdateLogAdmin(admin.ModelAdmin):
    list_display = ("company", "pinned", "title", "visible_to_client", "created_at")
    list_filter = ("visible_to_client", "pinned")
    search_fields = ("company__name", "title", "body")
    autocomplete_fields = ("company", "created_by")

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))

@admin.register(PortalInvite)
class PortalInviteAdmin(admin.ModelAdmin):
    list_display = ("company", "email", "token", "created_at", "expires_at", "used")
    list_filter = ("used",)
    search_fields = ("company__name", "email", "token")
    autocomplete_fields = ("company",)

    readonly_fields = ("token", "created_at", "expires_at")

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return is_owner(request.user)

@admin.register(ProposalDocument)
class ProposalDocumentAdmin(admin.ModelAdmin):
    list_display = ("company", "title", "version", "is_active", "visible_to_client", "created_at")
    list_filter = ("is_active", "visible_to_client")
    search_fields = ("company__name", "title")
    autocomplete_fields = ("company", "created_by")
    readonly_fields = ("created_at", "updated_at")

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))

@admin.register(RoadMap)
class RoadMapAdmin(admin.ModelAdmin):
    list_display = ("company", "title", "version", "is_active", "visible_to_client", "created_at")
    list_filter = ("is_active", "visible_to_client")
    search_fields = ("company__name", "title")
    autocomplete_fields = ("company", "created_by")
    readonly_fields = ("created_at", "updated_at")

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("company", "invoice_number", "title", "amount", "paid_at", "visible_to_client", "created_at")
    list_filter = ("visible_to_client",)
    search_fields = ("company__name", "invoice_number", "title")
    autocomplete_fields = ("company", "created_by")
    readonly_fields = ("created_at", "updated_at")

    def has_module_permission(self, request):
        return request.user.is_staff and (is_owner(request.user) or is_staff_role(request.user))
