from django import forms
from django.forms import ModelForm
from .models import Prospect

def _field_exists(model, name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())

def _first_present(model, candidates):
    for c in candidates:
        if _field_exists(model, c):
            return c
    return None

class ProspectForm(forms.ModelForm):
    class Meta:
        model = Prospect
        fields = [
            "full_name", "email", "phone",
            "company_name", "status", "notes"
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        return email.lower()

class ProspectEditForm(ModelForm):
    new_note_subject = forms.CharField(max_length=160, required=False, label="Add note — subject")
    new_note_body_md = forms.CharField(
        required=False,
        label="Add note — details (Markdown)",
        widget=forms.Textarea(attrs={"rows": 3})
    )
    class Meta:
        model = Prospect
        fields = [
            "company_name",
            "full_name",
            "email",
            "phone",
            "website_url",
            "address1", "address2", "city", "state", "postal_code", "country",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_contact_email(self):
        email = (self.cleaned_data.get("contact_email") or "").strip().lower()
        return email

class ProspectStatusForm(ModelForm):
    new_note_subject = forms.CharField(max_length=160, required=False, label="Add note — subject")
    new_note_body_md = forms.CharField(
        required=False,
        label="Add note — details (Markdown)",
        widget=forms.Textarea(attrs={"rows": 3})
    )
    class Meta:
        model = Prospect
        fields = [
            "status",
            "last_contacted_at",
            "next_follow_up_at",
            "notes",
        ]
        widgets = {
            "last_contacted_at": forms.DateInput(attrs={"type": "date"}),
            "next_follow_up_at": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        return cleaned
    
class ProspectNoteQuickForm(forms.Form):
    subject = forms.CharField(max_length=160, required=False, label="Note subject")
    body_md = forms.CharField(
        required=False,
        label="Note details (Markdown)",
        widget=forms.Textarea(attrs={"rows": 4})
    )
    is_pinned = forms.BooleanField(required=False, initial=False, label="Pin this note")