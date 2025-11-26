# prospectApp/forms.py
from django import forms
from django.forms import ModelForm
from .models import Prospect


class ProspectForm(ModelForm):
    class Meta:
        model = Prospect
        fields = [
            "full_name",
            "company_name",
            "email",
            "phone",
            "website_url",
            "sheet_url",
            "status",
            "notes",
            "tags",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email
