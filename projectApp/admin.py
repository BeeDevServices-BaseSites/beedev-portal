# projectApp/admin.py
from django.contrib import admin, messages
from django.db.models import Count, Q
from django.utils.html import format_html
from .models import (
    Project, ProjectMember, Sprint, ProjectTask, ProjectMilestone,
    ProjectUpdate, ProjectUpdateAttachment, ProjectEnvironment,
    ProjectLink, ProjectViewer, ProjectWeekNote,
    TaskComment, TaskChecklistItem, TaskAttachment, Notification
)

# ============================================================
# Inlines
# ============================================================

class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    autocomplete_fields = ("user",)
    fields = ("user", "role", "is_active", "added_at")
    readonly_fields = ("added_at",)

class ProjectEnvironmentInline(admin.TabularInline):
    model = ProjectEnvironment
    extra = 0
    fields = ("kind", "url", "health", "note", "last_checked_at", "last_updated_by")
    autocomplete_fields = ("last_updated_by",)
    readonly_fields = ("last_checked_at",)

class ProjectLinkInline(admin.TabularInline):
    model = ProjectLink
    extra = 0
    fields = ("label", "url", "section", "visibility", "is_active", "sort_order", "notes")

class ProjectMilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 0
    fields = ("name", "state", "due_date", "completed_at", "is_client_visible", "sort_order")
    readonly_fields = ("completed_at",)

class SprintInline(admin.TabularInline):
    model = Sprint
    extra = 0
    fields = ("name", "start_date", "end_date", "goal", "is_active")

class TaskChecklistInline(admin.TabularInline):
    model = TaskChecklistItem
    extra = 0
    fields = ("text", "done", "sort_order", "created_by", "created_at")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at",)

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    fields = ("file", "original_name", "uploaded_by", "uploaded_at")
    autocomplete_fields = ("uploaded_by",)
    readonly_fields = ("uploaded_at",)

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    fk_name = "task"
    extra = 0
    fields = ("author", "parent", "is_internal", "body", "created_at", "edited_at")
    autocomplete_fields = ("author", "parent")
    readonly_fields = ("created_at", "edited_at")

class UpdateAttachmentInline(admin.TabularInline):
    model = ProjectUpdateAttachment
    extra = 0
    fields = ("file", "original_name", "uploaded_at")
    readonly_fields = ("uploaded_at",)

# ============================================================
# Actions
# ============================================================

def _set_task_status(modeladmin, request, queryset, status_value, label):
    updated = queryset.update(status=status_value)
    messages.success(request, f"{updated} task(s) moved to {label}.")

@admin.action(description="Set status → To Do")
def action_tasks_todo(modeladmin, request, queryset):
    from .models import ProjectTask
    _set_task_status(modeladmin, request, queryset, ProjectTask.Status.TODO, "To Do")

@admin.action(description="Set status → In Progress")
def action_tasks_in_progress(modeladmin, request, queryset):
    from .models import ProjectTask
    _set_task_status(modeladmin, request, queryset, ProjectTask.Status.IN_PROGRESS, "In Progress")

@admin.action(description="Set status → Blocked")
def action_tasks_blocked(modeladmin, request, queryset):
    from .models import ProjectTask
    _set_task_status(modeladmin, request, queryset, ProjectTask.Status.BLOCKED, "Blocked")

@admin.action(description="Set status → Done")
def action_tasks_done(modeladmin, request, queryset):
    from .models import ProjectTask
    _set_task_status(modeladmin, request, queryset, ProjectTask.Status.DONE, "Done")

@admin.action(description="Set status → Canceled")
def action_tasks_canceled(modeladmin, request, queryset):
    from .models import ProjectTask
    _set_task_status(modeladmin, request, queryset, ProjectTask.Status.CANCELED, "Canceled")

@admin.action(description="Clear sprint (move to Backlog)")
def action_tasks_clear_sprint(modeladmin, request, queryset):
    updated = queryset.update(sprint=None)
    messages.success(request, f"{updated} task(s) moved to Backlog.")

@admin.action(description="Mark notifications as read")
def action_notifications_mark_read(modeladmin, request, queryset):
    updated = queryset.update(is_read=True)
    messages.success(request, f"{updated} notification(s) marked as read.")

# ============================================================
# Admin registrations
# ============================================================

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "company", "name", "status", "stage", "manager",
        "percent_complete", "priority", "is_active", "link_count", "env_count", "task_summary",
        "created_at",
    )
    list_filter = ("status", "stage", "is_active", "priority", "client_can_view_status", "client_can_view_links")
    search_fields = ("name", "slug", "description", "scope_summary", "company__name")
    autocomplete_fields = ("company", "proposal", "manager", "created_by")
    readonly_fields = ("created_at", "updated_at", "slug")
    inlines = [ProjectMemberInline, ProjectEnvironmentInline, ProjectLinkInline, ProjectMilestoneInline, SprintInline]
    ordering = ("company__name", "name")

    fieldsets = (
        ("Basics", {
            "fields": ("company", "proposal", "name", "slug", "description", "scope_summary", "tags")
        }),
        ("Status", {
            "fields": ("status", "stage", "manager", "priority", "show_priority_to_client", "is_active")
        }),
        ("Dates", {
            "fields": ("start_date", "target_launch_date", "actual_launch_date")
        }),
        ("Client Visibility", {
            "fields": ("client_can_view_status", "client_can_view_links", "client_can_view_description")
        }),
        ("Progress", {
            "fields": ("percent_complete",)
        }),
        ("Meta", {
            "fields": ("created_by", "created_at", "updated_at")
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # annotate for quick counts and status summary
        qs = qs.annotate(
            link_cnt=Count("links", filter=Q(links__is_active=True)),
            env_cnt=Count("environments"),
            todo_cnt=Count("tasks", filter=Q(tasks__status=ProjectTask.Status.TODO)),
            inprog_cnt=Count("tasks", filter=Q(tasks__status=ProjectTask.Status.IN_PROGRESS)),
            blocked_cnt=Count("tasks", filter=Q(tasks__status=ProjectTask.Status.BLOCKED)),
            done_cnt=Count("tasks", filter=Q(tasks__status=ProjectTask.Status.DONE)),
        )
        return qs

    def link_count(self, obj):
        return obj.link_cnt
    link_count.short_description = "Links"

    def env_count(self, obj):
        return obj.env_cnt
    env_count.short_description = "Envs"

    def task_summary(self, obj):
        return f"📝 {obj.todo_cnt} · 🔧 {obj.inprog_cnt} · ⛔ {obj.blocked_cnt} · ✅ {obj.done_cnt}"
    task_summary.short_description = "Tasks"

@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "is_active", "added_at")
    list_filter = ("role", "is_active")
    search_fields = ("project__name", "project__slug", "user__username", "user__preferred_name")
    autocomplete_fields = ("project", "user")
    readonly_fields = ("added_at",)

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "start_date", "end_date", "goal", "is_active")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("name", "goal", "project__name", "project__slug")
    autocomplete_fields = ("project",)

@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = (
        "project", "title", "status", "priority", "sprint",
        "due_date", "planned_week_start", "percent_complete", "estimated_hours",
        "assignees_list", "created_at"
    )
    list_filter = (
        "project", "status", "priority", "sprint", "is_client_visible",
        ("due_date", admin.DateFieldListFilter), ("planned_week_start", admin.DateFieldListFilter)
    )
    search_fields = ("title", "description", "project__name", "project__slug")
    autocomplete_fields = ("project", "assignees", "sprint", "created_by")
    inlines = [TaskChecklistInline, TaskAttachmentInline, TaskCommentInline]
    readonly_fields = ("created_at", "updated_at")
    actions = [
        action_tasks_todo, action_tasks_in_progress, action_tasks_blocked,
        action_tasks_done, action_tasks_canceled, action_tasks_clear_sprint
    ]
    ordering = ("project", "priority", "due_date", "pk")

    fieldsets = (
        ("Basics", {
            "fields": ("project", "title", "description")
        }),
        ("Planning", {
            "fields": ("priority", "status", "sprint", "story_points", "blocked_reason")
        }),
        ("Schedule", {
            "fields": ("due_date", "planned_week_start")
        }),
        ("Assignment", {
            "fields": ("assignees",)
        }),
        ("Tracking", {
            "fields": ("estimated_hours", "percent_complete", "sort_order")
        }),
        ("Client Visibility", {
            "fields": ("is_client_visible", "show_priority_to_client")
        }),
        ("Meta", {
            "fields": ("created_by", "created_at", "updated_at")
        }),
    )

    def assignees_list(self, obj):
        names = [getattr(u, "preferred_name", None) or u.get_username() for u in obj.assignees.all()]
        return ", ".join(names) if names else "—"
    assignees_list.short_description = "Assignees"

@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "state", "due_date", "completed_at", "is_client_visible", "sort_order")
    list_filter = ("state", "is_client_visible", ("due_date", admin.DateFieldListFilter))
    search_fields = ("name", "project__name", "project__slug")
    autocomplete_fields = ("project",)

@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(admin.ModelAdmin):
    list_display = ("project", "title", "visibility", "percent_complete_snapshot", "pinned", "posted_at", "created_by")
    list_filter = ("visibility", "pinned", ("posted_at", admin.DateFieldListFilter))
    search_fields = ("title", "body", "project__name", "project__slug")
    autocomplete_fields = ("project", "created_by")
    inlines = [UpdateAttachmentInline]
    readonly_fields = ("posted_at",)

@admin.register(ProjectWeekNote)
class ProjectWeekNoteAdmin(admin.ModelAdmin):
    list_display = ("project", "week_start", "visibility", "created_by", "created_at")
    list_filter = ("visibility", ("week_start", admin.DateFieldListFilter))
    search_fields = ("project__name", "project__slug", "body")
    autocomplete_fields = ("project", "created_by")
    readonly_fields = ("created_at",)

@admin.register(ProjectEnvironment)
class ProjectEnvironmentAdmin(admin.ModelAdmin):
    list_display = ("project", "kind", "url_link", "health", "note", "last_checked_at", "last_updated_by")
    list_filter = ("kind", "health")
    search_fields = ("project__name", "project__slug", "url", "note")
    autocomplete_fields = ("project", "last_updated_by")

    def url_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">Open</a>', obj.url)
        return "—"
    url_link.short_description = "URL"

@admin.register(ProjectLink)
class ProjectLinkAdmin(admin.ModelAdmin):
    list_display = ("project", "label", "section", "visibility", "is_active", "sort_order")
    list_filter = ("visibility", "section", "is_active")
    search_fields = ("label", "url", "notes", "project__name", "project__slug")
    autocomplete_fields = ("project",)

@admin.register(ProjectViewer)
class ProjectViewerAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "granted_by", "granted_at")
    list_filter = (("granted_at", admin.DateFieldListFilter),)
    search_fields = ("project__name", "project__slug", "user__username", "user__preferred_name")
    autocomplete_fields = ("project", "user", "granted_by")
    readonly_fields = ("granted_at",)

@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "is_internal", "created_at")
    list_filter = ("is_internal", ("created_at", admin.DateFieldListFilter))
    search_fields = ("body", "task__title", "task__project__name", "author__username", "author__preferred_name")
    autocomplete_fields = ("task", "author", "parent")
    readonly_fields = ("created_at", "edited_at")

@admin.register(TaskChecklistItem)
class TaskChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("task", "text", "done", "sort_order", "created_by", "created_at")
    list_filter = ("done",)
    search_fields = ("text", "task__title", "task__project__name")
    autocomplete_fields = ("task", "created_by")
    readonly_fields = ("created_at",)

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "original_name", "uploaded_by", "uploaded_at")
    list_filter = (("uploaded_at", admin.DateFieldListFilter),)
    search_fields = ("original_name", "task__title", "task__project__name")
    autocomplete_fields = ("task", "uploaded_by")
    readonly_fields = ("uploaded_at",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "kind", "task", "is_read", "created_at", "message")
    list_filter = ("kind", "is_read", ("created_at", admin.DateFieldListFilter))
    search_fields = ("message", "recipient__username", "recipient__preferred_name", "task__title", "task__project__name")
    autocomplete_fields = ("recipient", "task")
    actions = [action_notifications_mark_read]
    readonly_fields = ("created_at",)
