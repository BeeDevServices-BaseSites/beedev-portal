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
        # Adjust this list to your model’s real fields
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
    """
    General info edit (company/contact/notes/etc.).
    Tries to include sensible fields if they exist on your Prospect model.
    """
    class Meta:
        model = Prospect
        # Try common field names; only include those that exist on your model.
        fields = [f for f in [
            _first_present(Prospect, ["company_name", "name"]),
            "contact_name",
            "contact_email",
            "phone",
            "website",
            "notes",
            # optional “do not contact” fields if you added them
            "dnc_email",
            "dnc_phone",
            "dnc_reason",
        ] if f and _field_exists(Prospect, f)]

    def clean_contact_email(self):
        email_field = "contact_email"
        if _field_exists(Prospect, email_field):
            val = (self.cleaned_data.get(email_field) or "").strip().lower()
            return val
        return self.cleaned_data.get(email_field)

class ProspectStatusForm(ModelForm):
    """
    Status-only form (e.g., NEW/ACTIVE/WON/LOST/etc.).
    """
    class Meta:
        model = Prospect
        fields = ["status"] if _field_exists(Prospect, "status") else []

    def clean(self):
        cleaned = super().clean()
        # You can add per-status validation here if needed
        return cleaned