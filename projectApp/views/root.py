# projectApp/views.py
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.db.models import Q
from core.utils.context import base_ctx

from ..models import (
    Project, ProjectTask, Sprint, TaskComment, TaskChecklistItem, TaskAttachment
)
from ..forms import (
    TaskCommentForm, TaskChecklistItemForm, TaskAttachmentForm,
    TaskMoveForm, TaskAssignSprintForm, ProjectCreateForm
)

# ---------------- Permissions ----------------

def _can_view_project(user, project: Project) -> bool:
    if not user.is_authenticated:
        return False
    role = getattr(user, "role", None)
    if role in {user.Roles.OWNER, user.Roles.ADMIN, user.Roles.EMPLOYEE, user.Roles.HR}:
        return True
    if project.members.filter(user=user, is_active=True).exists():
        return True
    if project.viewers.filter(user=user).exists():
        return True
    return False

def _can_edit_project(user, project: Project) -> bool:
    if not user.is_authenticated:
        return False
    role = getattr(user, "role", None)
    if role in {user.Roles.OWNER, user.Roles.ADMIN, user.Roles.EMPLOYEE}:
        return True
    if project.members.filter(user=user, is_active=True).exists():
        return True
    return False

def _assert_view_perm(user, project):
    if not _can_view_project(user, project):
        raise PermissionDenied("Not allowed")

def _assert_edit_perm(user, project):
    if not _can_edit_project(user, project):
        raise PermissionDenied("Not allowed")
    
def _can_admin_projects(user) -> bool:
    role = getattr(user, "role", None)
    return role in {user.Roles.OWNER, user.Roles.ADMIN, user.Roles.EMPLOYEE, user.Roles.HR}

# ---------------- Base ----------------
@login_required
def project_home(request):
    if not _can_admin_projects(request.user):
        raise PermissionDenied("Not allowed")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    company = request.GET.get("company", "").strip()
    active = request.GET.get("active", "").strip()  # "", "1", "0"

    projects = Project.objects.select_related("company", "proposal", "manager").order_by("company__name", "name")

    if q:
        projects = projects.filter(
            Q(name__icontains=q) |
            Q(slug__icontains=q) |
            Q(description__icontains=q) |
            Q(scope_summary__icontains=q) |
            Q(company__name__icontains=q) |
            Q(tags__icontains=q)
        )
    if status:
        projects = projects.filter(status=status)
    if company:
        projects = projects.filter(company_id=company)
    if active in {"1", "0"}:
        projects = projects.filter(is_active=(active == "1"))

    paginator = Paginator(projects, 20)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    statuses = Project.Status.choices
    companies = Project.objects.values("company_id", "company__name").distinct().order_by("company__name")

    title = "Projects"
    ctx = dict(page_obj=page_obj, q=q, status=status, statuses=statuses, companies=companies, active=active)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp_staff/project_home.html", ctx)

@login_required
def project_create(request):
    if not _can_admin_projects(request.user):
        raise PermissionDenied("Not allowed")

    if request.method == "POST":
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            proj = form.save(commit=False)
            proj.created_by = request.user
            proj.save()
            messages.success(request, "Project created.")
            return redirect("projectApp:board", slug=proj.slug)
        messages.error(request, "Please fix the errors below.")
    else:
        form = ProjectCreateForm()

    title = "Create Project"
    ctx = dict(form=form)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp/project_create.html", ctx)

# ---------------- Board & My Tasks ----------------
@login_required
def project_board(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    _assert_view_perm(request.user, project)

    active_sprint = project.sprints.filter(is_active=True).order_by("start_date").first()
    tasks_qs = project.tasks.select_related("sprint").prefetch_related("assignees")

    if active_sprint:
        tasks_qs = tasks_qs.filter(sprint=active_sprint)
    else:
        tasks_qs = tasks_qs.filter(sprint__isnull=True)

    cols = {
        "TODO": tasks_qs.filter(status=ProjectTask.Status.TODO),
        "IN_PROGRESS": tasks_qs.filter(status=ProjectTask.Status.IN_PROGRESS),
        "BLOCKED": tasks_qs.filter(status=ProjectTask.Status.BLOCKED),
        "DONE": tasks_qs.filter(status=ProjectTask.Status.DONE),
        "CANCELED": tasks_qs.filter(status=ProjectTask.Status.CANCELED),
    }

    title = f"{project.name} · Board"
    ctx = dict(project=project, active_sprint=active_sprint, cols=cols)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp_staff/board.html", ctx)

@login_required
def my_tasks(request):
    user = request.user
    tasks = (
        ProjectTask.objects.filter(assignees=user)
        .select_related("project", "sprint")
        .prefetch_related("assignees")
        .order_by("project__name", "priority", "due_date", "pk")
    )
    title = "My Tasks"
    ctx = dict(tasks=tasks)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp_staff/my_tasks.html", ctx)

# ---------------- Task Detail & Interactions ----------------

@login_required
def task_detail(request, pk: int):
    task = get_object_or_404(
        ProjectTask.objects.select_related("project", "sprint")
        .prefetch_related("assignees",
                          Prefetch("comments", queryset=TaskComment.objects.select_related("author", "parent").order_by("created_at", "pk")),
                          Prefetch("checklist", queryset=TaskChecklistItem.objects.order_by("sort_order", "pk")),
                          "attachments"),
        pk=pk
    )
    project = task.project
    _assert_view_perm(request.user, project)

    comment_form = TaskCommentForm()
    checklist_form = TaskChecklistItemForm()
    attach_form = TaskAttachmentForm()
    move_form = TaskMoveForm(initial={"status": task.status})
    sprint_form = TaskAssignSprintForm(project=project, initial={"sprint": task.sprint_id})

    title = f"Task · {task.title}"
    ctx = dict(
        task=task,
        comment_form=comment_form,
        checklist_form=checklist_form,
        attach_form=attach_form,
        move_form=move_form,
        sprint_form=sprint_form,
    )
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp_staff/task_detail.html", ctx)

@require_POST
@login_required
def task_add_comment(request, pk: int):
    task = get_object_or_404(ProjectTask, pk=pk)
    _assert_edit_perm(request.user, task.project)

    form = TaskCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.task = task
        comment.author = request.user
        comment.save()
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Could not add comment. Please fix errors.")

    return redirect("projectApp_staff:task_detail", pk=task.pk)

@require_POST
@login_required
def task_add_checklist_item(request, pk: int):
    task = get_object_or_404(ProjectTask, pk=pk)
    _assert_edit_perm(request.user, task.project)

    form = TaskChecklistItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.task = task
        item.created_by = request.user
        item.save()
        messages.success(request, "Checklist item added.")
    else:
        messages.error(request, "Could not add checklist item.")
    return redirect("projectApp:task_detail", pk=task.pk)

@require_POST
@login_required
def task_toggle_checklist_item(request, item_id: int):
    item = get_object_or_404(TaskChecklistItem.objects.select_related("task", "task__project"), pk=item_id)
    _assert_edit_perm(request.user, item.task.project)

    item.done = not item.done
    item.save(update_fields=["done"])
    return redirect("projectApp:task_detail", pk=item.task.pk)

@require_POST
@login_required
def task_upload_attachment(request, pk: int):
    task = get_object_or_404(ProjectTask, pk=pk)
    _assert_edit_perm(request.user, task.project)

    form = TaskAttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        att = form.save(commit=False)
        att.task = task
        att.uploaded_by = request.user
        att.save()
        messages.success(request, "Attachment uploaded.")
    else:
        messages.error(request, "Upload failed.")
    return redirect("projectApp:task_detail", pk=task.pk)

@require_POST
@login_required
def task_move_status(request, pk: int):
    task = get_object_or_404(ProjectTask.objects.select_related("project"), pk=pk)
    _assert_edit_perm(request.user, task.project)

    form = TaskMoveForm(request.POST)
    if form.is_valid():
        task.status = form.cleaned_data["status"]
        task.save(update_fields=["status"])
        messages.success(request, "Task status updated.")
    else:
        messages.error(request, "Invalid status.")
    return redirect("projectApp:task_detail", pk=task.pk)

@require_POST
@login_required
def task_assign_sprint(request, pk: int):
    task = get_object_or_404(ProjectTask.objects.select_related("project"), pk=pk)
    _assert_edit_perm(request.user, task.project)

    form = TaskAssignSprintForm(request.POST, project=task.project)
    if form.is_valid():
        task.sprint = form.cleaned_data["sprint"]  # None = backlog
        task.save(update_fields=["sprint"])
        messages.success(request, "Sprint assignment updated.")
    else:
        messages.error(request, "Could not update sprint.")
    return redirect("projectApp:task_detail", pk=task.pk)
