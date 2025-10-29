# projectApp/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import TaskComment, TaskChecklistItem, TaskAttachment, ProjectTask, Sprint, Project, ProjectMember

User = get_user_model()

class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = (
            "company", "proposal", "name", "description", "scope_summary",
            "manager", "priority", "status", "stage",
            "start_date", "target_launch_date",
            "client_can_view_status", "client_can_view_links", "client_can_view_description",
            "tags",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional summary for internal team"}),
            "scope_summary": forms.Textarea(attrs={"rows": 3, "placeholder": "High-level scope (client-safe)"}),
        }

class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ("body", "is_internal")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Write a comment…"}),
        }

class TaskChecklistItemForm(forms.ModelForm):
    class Meta:
        model = TaskChecklistItem
        fields = ("text",)

class TaskAttachmentForm(forms.ModelForm):
    class Meta:
        model = TaskAttachment
        fields = ("file", "original_name")
        widgets = {
            "original_name": forms.TextInput(attrs={"placeholder": "Optional display name"}),
        }

class TaskMoveForm(forms.Form):
    status = forms.ChoiceField(choices=ProjectTask.Status.choices)

class TaskAssignSprintForm(forms.Form):
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields["sprint"].queryset = project.sprints.all().order_by("-is_active", "start_date")

class ProjectMemberAddForm(forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ("user", "role", "is_active")
    # Limit user choices (optional: only staff or active users)
    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(is_active=True).order_by("username")

class QuickTaskForm(forms.ModelForm):
    class Meta:
        model = ProjectTask
        fields = ("title", "description", "priority", "due_date", "assignees")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "Optional description"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignees"].queryset = User.objects.filter(is_active=True).order_by("username")

class SprintForm(forms.ModelForm):
    class Meta:
        model = Sprint
        fields = ("name", "start_date", "end_date", "goal", "is_active")
        widgets = {
            "goal": forms.TextInput(attrs={"placeholder": "Optional sprint goal"}),
        }

class MoveManyForm(forms.Form):
    """Move many tasks to a new status or sprint."""
    status = forms.ChoiceField(choices=[("", "— keep —")] + list(ProjectTask.Status.choices), required=False)
    sprint = forms.ModelChoiceField(queryset=Sprint.objects.none(), required=False)
    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields["sprint"].queryset = project.sprints.all().order_by("-is_active", "start_date")