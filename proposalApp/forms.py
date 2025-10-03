# proposalApp/forms.py
from django import forms
from django.forms import formset_factory, inlineformset_factory
from companyApp.models import Company
from .models import ProposalDraft, Discount, DraftNote

# -------------------------
# Draft header form (create & edit)
# -------------------------
class DraftForm(forms.ModelForm):
    class Meta:
        model = ProposalDraft
        fields = [
            "company", "title", "currency", "discount",
            "contact_name", "contact_email",
        ]
        labels = {
            "company": "Company",
            "title": "Draft title",
            "currency": "Currency",
            "discount": "Discount",
            "contact_name": "Primary contact name",
            "contact_email": "Primary contact email",
        }
        widgets = {
            "company": forms.Select(attrs={"required": "required", "id": "id_company"}),
            "title": forms.TextInput(attrs={"required": "required"}),
            "currency": forms.TextInput(attrs={"maxlength": 8}),
            "discount": forms.Select(),
            "contact_name": forms.TextInput(attrs={"id": "id_contact_name"}),
            "contact_email": forms.EmailInput(attrs={"id": "id_contact_email"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["discount"].queryset = Discount.objects.filter(is_active=True)
        self.fields["discount"].required = False
        if not self.instance.pk:
            self.fields["currency"].initial = "USD"

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get("company")
        title = (cleaned.get("title") or "").strip()

        if not company:
            self.add_error("company", "Select a company.")
        if not title:
            self.add_error("title", "Enter a title.")

        if company:
            if not cleaned.get("contact_name"):
                cleaned["contact_name"] = company.primary_contact_name or ""
            if not cleaned.get("contact_email"):
                cleaned["contact_email"] = (company.primary_email or "").strip().lower()

        return cleaned

NewDraftForm = DraftForm


# --------------------------------
# Notes (create flow: plain FormSet)
# --------------------------------
class DraftNoteForm(forms.Form):
    subject = forms.CharField(max_length=160, required=False, label="Section title")
    body_md = forms.CharField(
        required=False,
        label="Details (Markdown)",
        widget=forms.Textarea(attrs={"rows": 4})
    )
    sort_order = forms.IntegerField(required=False, min_value=0, initial=0, label="Sort order")

DraftNoteFormSet = formset_factory(
    DraftNoteForm,
    extra=1,
    can_delete=True,
)


# -------------------------------------------
# Notes (edit flow: inline ModelFormSet)
# -------------------------------------------
DraftNoteInlineFormSet = inlineformset_factory(
    parent_model=ProposalDraft,
    model=DraftNote,
    fields=["subject", "body_md", "sort_order"],
    extra=0,
    can_delete=True,
    widgets={
        "body_md": forms.Textarea(attrs={"rows": 4}),
    },
)
