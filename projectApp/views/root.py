# projectApp/views.py
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Prefetch, Max, Q
from django.core.paginator import Paginator
from core.utils.context import base_ctx
from django.views.decorators.http import require_http_methods, require_POST
from django.forms import modelform_factory
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from django.http import JsonResponse
from companyApp.models import Company
from ..models import (
    Project, ProjectTask, Sprint, TaskComment, TaskChecklistItem, TaskAttachment, ProjectMember
)
from ..forms import (
    TaskCommentForm, TaskChecklistItemForm, TaskAttachmentForm,
    TaskMoveForm, TaskAssignSprintForm, ProjectCreateForm, ProjectMemberAddForm, QuickTaskForm, SprintForm, MoveManyForm
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
    company_filter = request.GET.get("company", "").strip()
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
    if company_filter:
        projects = projects.filter(company_id=company_filter)
    if active in {"1", "0"}:
        projects = projects.filter(is_active=(active == "1"))

    paginator = Paginator(projects, 20)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    statuses = Project.Status.choices
    companies = Company.objects.order_by("name").only("id", "name")

    title = "Projects"
    ctx = dict(page_obj=page_obj, q=q, status=status, statuses=statuses, companies=companies, company_filter=company_filter, active=active)
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
            return redirect("projects_staff:project_board", slug=proj.slug)
        messages.error(request, "Please fix the errors below.")
    else:
        form = ProjectCreateForm()

    title = "Create Project"
    ctx = dict(form=form)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp_staff/project_create.html", ctx)

# ---------------- Board & My Tasks ----------------
@ensure_csrf_cookie
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
def _current_board_scope(project: Project):
    return project.sprints.filter(is_active=True).order_by("start_date").first()

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

@login_required
@require_http_methods(["GET", "POST"])
def project_manage_members(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    _assert_edit_perm(request.user, project)

    if request.method == "POST":
        form = ProjectMemberAddForm(request.POST, project=project)
        if form.is_valid():
            pm = form.save(commit=False)
            pm.project = project
            pm_existing = ProjectMember.objects.filter(project=project, user=pm.user).first()
            if pm_existing:
                pm_existing.role = pm.role
                pm_existing.is_active = pm.is_active
                pm_existing.save(update_fields=["role", "is_active"])
                messages.success(request, "Member updated.")
            else:
                pm.save()
                messages.success(request, "Member added.")
            return redirect("projectApp:board", slug=slug)
        messages.error(request, "Please fix errors below.")
    else:
        form = ProjectMemberAddForm(project=project)

    members = project.members.select_related("user").order_by("role", "user__username")
    title = f"{project.name} · Members"
    ctx = dict(project=project, form=form, members=members)
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "projectApp_staff/manage_members.html", ctx)

@login_required
@require_POST
def project_quick_task_create(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    _assert_edit_perm(request.user, project)
    form = QuickTaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.project = project
        task.created_by = request.user
        active = project.sprints.filter(is_active=True).order_by("start_date").first()
        task.sprint = active
        task.save()
        form.save_m2m()
        messages.success(request, "Task created.")
    else:
        messages.error(request, "Could not create task—check the fields.")
    return redirect("projects_staff:project_board", slug=slug)

# --- Create or toggle a sprint on the board ---

@login_required
@require_http_methods(["POST"])
def project_create_sprint(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    _assert_edit_perm(request.user, project)
    form = SprintForm(request.POST)
    if form.is_valid():
        s = form.save(commit=False)
        s.project = project
        s.save()
        messages.success(request, "Sprint created.")
    else:
        messages.error(request, "Sprint not created—please fix errors.")
    return redirect("projects_staff:project_board", slug=slug)

@login_required
@require_POST
def project_toggle_active_sprint(request, slug: str, sprint_id: int):
    project = get_object_or_404(Project, slug=slug)
    _assert_edit_perm(request.user, project)
    sprint = get_object_or_404(Sprint, pk=sprint_id, project=project)
    sprint.is_active = not sprint.is_active
    sprint.save(update_fields=["is_active"])
    messages.success(request, f"Sprint '{sprint.name}' is now {'active' if sprint.is_active else 'inactive'}.")
    return redirect("projects_staff:project_board", slug=slug)

# --- Bulk move helper (optional) ---

@login_required
@require_POST
def project_bulk_move(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    _assert_edit_perm(request.user, project)
    form = MoveManyForm(request.POST, project=project)
    task_ids = request.POST.getlist("task_ids")
    if not task_ids:
        messages.info(request, "No tasks selected.")
        return redirect("projects_staff:project_board", slug=slug)
    if form.is_valid():
        with transaction.atomic():
            qs = ProjectTask.objects.filter(project=project, pk__in=task_ids)
            status = form.cleaned_data["status"]
            sprint = form.cleaned_data["sprint"]
            updates = {}
            if status:
                updates["status"] = status
            if "sprint" in form.cleaned_data:
                updates["sprint"] = sprint
            if updates:
                qs.update(**updates)
        messages.success(request, f"Updated {len(task_ids)} task(s).")
    else:
        messages.error(request, "Invalid bulk update.")
    return redirect("projects_staff:project_board", slug=slug)

@require_POST
@login_required
def project_dnd_move(request, slug: str):
    project = get_object_or_404(Project, slug=slug)
    _assert_edit_perm(request.user, project)

    try:
        data = json.loads(request.body.decode("utf-8"))
        task_id = data.get("task_id")
        to_status = data.get("to_status")
        after_id = data.get("after_id")

        if not task_id or not to_status:
            return JsonResponse({"ok": False, "error": "Missing fields"}, status=400)

        task = get_object_or_404(ProjectTask, pk=task_id, project=project)

        active_sprint = _current_board_scope(project)
        scope_filter = {"project": project, "sprint": active_sprint} if active_sprint else {"project": project, "sprint__isnull": True}

        with transaction.atomic():
            # Save new status first
            task.status = to_status
            task.save(update_fields=["status"])

            # Lock the target column (excluding the moving task)
            col_qs = (
                ProjectTask.objects
                .select_for_update()
                .filter(**scope_filter, status=to_status)
                .exclude(pk=task.pk)
                .order_by("sort_order", "pk")
            )

            # Rebuild exact DOM order
            ordered = list(col_qs)
            if after_id:
                inserted = False
                aid = int(after_id)
                for idx, t in enumerate(ordered):
                    if t.pk == aid:
                        ordered.insert(idx + 1, task)
                        inserted = True
                        break
                if not inserted:
                    ordered.append(task)
            else:
                ordered.insert(0, task)

            # Normalize to multiples of 10 (pure python ints)
            for i, t in enumerate(ordered, start=1):
                new_order = i * 10  # int
                if t.sort_order != new_order:
                    t.sort_order = new_order
                    t.save(update_fields=["sort_order"])

        return JsonResponse({"ok": True})

    except Exception as e:
        # TEMP: surface the exact server error in the client to pinpoint source
        return JsonResponse({"ok": False, "error": f"{type(e).__name__}: {e}"}, status=500)