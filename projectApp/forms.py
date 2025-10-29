# projectApp/forms.py
from django import forms
from .models import TaskComment, TaskChecklistItem, TaskAttachment, ProjectTask, Sprint, Project

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
