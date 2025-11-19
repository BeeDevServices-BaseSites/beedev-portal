# ticketApp/admin.py

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.utils.http import urlencode
from django.db.models import Count, Q

from .models import Ticket, TicketMessage, TicketAttachment, TicketEvent
from companyApp.models import CompanyMember
from userApp.models import User


# ---------- permission helpers ----------

def is_owner(user):
    return user.is_active and (user.is_superuser or getattr(user, "role", None) == User.Roles.OWNER)


def is_staff_role(user):
    return user.is_active and getattr(user, "role", None) in {User.Roles.OWNER, User.Roles.STAFF}


def can_edit(user):
    return is_staff_role(user)


# ============================ Inlines ============================

class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    fields = ("file", "original_name", "uploaded_at")
    readonly_fields = ("uploaded_at",)

    def has_delete_permission(self, request, obj=None):
        return can_edit(request.user)


class TicketMessageInline(admin.StackedInline):
    model = TicketMessage
    extra = 0
    fields = ("author", "author_kind", "is_internal", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    show_change_link = True

    def has_delete_permission(self, request, obj=None):
        return can_edit(request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "author":
            ticket = getattr(request, "_current_ticket_obj", None)
            if ticket and ticket.pk:
                member_ids = CompanyMember.objects.filter(
                    company=ticket.company,
                    is_active=True,
                ).values_list("user_id", flat=True)
                field.queryset = field.queryset.filter(
                    Q(role__in=[User.Roles.STAFF, User.Roles.OWNER]) | Q(pk__in=member_ids)
                )
        return field


class TicketEventInline(admin.TabularInline):
    model = TicketEvent
    extra = 0
    can_delete = False
    fields = ("kind", "at", "actor", "data")
    readonly_fields = ("kind", "at", "actor", "data")
    show_change_link = False


# ============================ ModelAdmins ============================

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "public_key", "subject", "company", "project",
        "status", "priority", "assigned_to", "customer_user",
        "updated_at", "last_client_reply_at",
        "attachments_link",
        "attention_flag",
    )
    list_filter = ("status", "priority", "category")
    search_fields = (
        "public_key",
        "subject",
        "description",
        "company__name",
        "project__name",
        "assigned_to__username",
        "customer_user__username",
    )
    autocomplete_fields = ("company", "project", "customer_user", "created_by", "assigned_to", "watchers")

    inlines = [TicketMessageInline, TicketEventInline]

    readonly_fields = ("public_key", "created_at", "updated_at", "last_client_reply_at", "closed_at")

    fieldsets = (
        ("Ticket", {
            "fields": ("company", "project", "public_key", "subject", "description", "category"),
        }),
        ("Status", {
            "fields": ("status", "priority", "assigned_to"),
        }),
        ("Client & Audit", {
            "fields": (
                "customer_user",
                "created_by",
                "watchers",
                "last_client_reply_at",
                "closed_at",
                "created_at",
                "updated_at",
            ),
        }),
    )

    actions = [
        "set_open",
        "set_inprogress",
        "set_pending_client",
        "set_resolved",
        "set_closed",
        "assign_to_me",
    ]

    # ----- queryset annotation -----

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_attach_count=Count("messages__attachments"))

    # ----- list display helpers -----

    def attachments_link(self, obj):
        count = getattr(obj, "_attach_count", 0) or 0
        url = reverse(
            f"admin:{TicketAttachment._meta.app_label}_{TicketAttachment._meta.model_name}_changelist"
        )
        url = f"{url}?{urlencode({'message__ticket__id__exact': obj.id})}"
        return format_html('<a href="{}">{}</a>', url, f"{count} file(s)")
    attachments_link.short_description = "Attachments"

    def attention_flag(self, obj):
        if obj.status in (Ticket.Status.NEW, Ticket.Status.OPEN, Ticket.Status.INPROGRESS) and \
           obj.priority in (Ticket.Priority.HIGH, Ticket.Priority.URGENT):
            return format_html('<span style="color:#b91c1c;font-weight:600;">ATTN</span>')
        return ""
    attention_flag.short_description = ""

    # ----- permissions -----

    def has_module_permission(self, request):
        return request.user.is_authenticated and is_staff_role(request.user)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return can_edit(request.user)

    def has_change_permission(self, request, obj=None):
        return can_edit(request.user)

    def has_delete_permission(self, request, obj=None):
        return can_edit(request.user)

    # ----- actions -----

    def set_open(self, request, queryset):
        updated = queryset.update(status=Ticket.Status.OPEN)
        self.message_user(request, f"Marked {updated} ticket(s) OPEN.")
    set_open.short_description = "Mark OPEN"

    def set_inprogress(self, request, queryset):
        updated = queryset.update(status=Ticket.Status.INPROGRESS)
        self.message_user(request, f"Marked {updated} ticket(s) IN PROGRESS.")
    set_inprogress.short_description = "Mark IN PROGRESS"

    def set_pending_client(self, request, queryset):
        updated = queryset.update(status=Ticket.Status.PENDING)
        self.message_user(request, f"Marked {updated} ticket(s) PENDING CLIENT.")
    set_pending_client.short_description = "Mark PENDING CLIENT"

    def set_resolved(self, request, queryset):
        now = timezone.now()
        updated = 0
        for t in queryset:
            t.status = Ticket.Status.RESOLVED
            t.closed_at = now
            t.save(update_fields=["status", "closed_at", "updated_at"])
            updated += 1
        self.message_user(request, f"Marked {updated} ticket(s) RESOLVED.")
    set_resolved.short_description = "Mark RESOLVED"

    def set_closed(self, request, queryset):
        now = timezone.now()
        updated = 0
        for t in queryset:
            t.status = Ticket.Status.CLOSED
            t.closed_at = now
            t.save(update_fields=["status", "closed_at", "updated_at"])
            updated += 1
        self.message_user(request, f"Closed {updated} ticket(s).")
    set_closed.short_description = "Mark CLOSED"

    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f"Assigned {updated} ticket(s) to you.")
    assign_to_me.short_description = "Assign to me"

    # ----- field filtering -----

    def get_form(self, request, obj=None, **kwargs):
        request._current_ticket_obj = obj
        return super().get_form(request, obj, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == "watchers":
            ticket = getattr(request, "_current_ticket_obj", None)
            if ticket and ticket.pk:
                member_ids = CompanyMember.objects.filter(
                    company=ticket.company,
                    is_active=True,
                ).values_list("user_id", flat=True)
                field.queryset = field.queryset.filter(
                    Q(role__in=[User.Roles.STAFF, User.Roles.OWNER]) | Q(pk__in=member_ids)
                )
        return field

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        ticket = getattr(request, "_current_ticket_obj", None)

        if ticket and ticket.pk and db_field.name in ("assigned_to", "customer_user"):
            member_ids = CompanyMember.objects.filter(
                company=ticket.company,
                is_active=True,
            ).values_list("user_id", flat=True)

            if db_field.name == "assigned_to":
                field.queryset = field.queryset.filter(
                    Q(role__in=[User.Roles.STAFF, User.Roles.OWNER]) | Q(pk__in=member_ids)
                )
            else:
                field.queryset = field.queryset.filter(pk__in=member_ids)

        return field


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "author_kind", "is_internal", "created_at")
    list_filter = ("author_kind", "is_internal")
    search_fields = ("ticket__public_key", "ticket__subject", "body")
    autocomplete_fields = ("ticket", "author")
    readonly_fields = ("created_at",)
    inlines = [TicketAttachmentInline]

    def has_module_permission(self, request):
        return request.user.is_authenticated and is_staff_role(request.user)

    def has_add_permission(self, request):
        return can_edit(request.user)

    def has_change_permission(self, request, obj=None):
        return can_edit(request.user)

    def has_delete_permission(self, request, obj=None):
        return can_edit(request.user)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "original_name", "uploaded_at")
    search_fields = ("message__ticket__public_key", "original_name")
    autocomplete_fields = ("message",)
    readonly_fields = ("uploaded_at",)

    def has_module_permission(self, request):
        return request.user.is_authenticated and is_staff_role(request.user)

    def has_add_permission(self, request):
        return can_edit(request.user)

    def has_change_permission(self, request, obj=None):
        return can_edit(request.user)

    def has_delete_permission(self, request, obj=None):
        return can_edit(request.user)
