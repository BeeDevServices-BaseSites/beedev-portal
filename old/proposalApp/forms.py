# proposalApp/forms.py
from django import forms
from django.forms import formset_factory, inlineformset_factory, BaseInlineFormSet
from companyApp.models import Company
from .models import ProposalDraft, Discount, DraftNote, DraftItem
from django.contrib.auth import get_user_model

User = get_user_model()

class BaseDraftNoteFS(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            subj = (form.cleaned_data.get("subject") or "").strip()
            body = (form.cleaned_data.get("body_md") or "").strip()
            if not subj and not body:
                form.cleaned_data["DELETE"] = True

class SignProposalForm(forms.Form):
    full_name = forms.CharField(
        max_length=160,
        required=True,
        label="Your full name",
        widget=forms.TextInput(attrs={"placeholder": "Jane Doe"})
    )
    contact_email = forms.EmailField(
        required=False,
        label="Email for the signed copy",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"})
    )
    agree_e_records = forms.BooleanField(
        required=True,
        label="I agree to receive and sign this proposal electronically.",
        widget=forms.CheckboxInput(attrs={"class": "checkbox"})
    )
    agree_intent = forms.BooleanField(
        required=True,
        label="I intend to sign this proposal.",
        widget=forms.CheckboxInput(attrs={"class": "checkbox"})
    )
    def __init__(self, *args, **kwargs):
        self.proposal = kwargs.pop("proposal", None)
        super().__init__(*args, **kwargs)
        if self.proposal and not self.initial.get("contact_email"):
            self.initial["contact_email"] = getattr(self.proposal, "contact_email", "")

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

class DraftForm(forms.ModelForm):
    class Meta:
        model = ProposalDraft
        fields = [
            "company", "title", "currency", "discount",
            "contact_name", "contact_email", "summary_md",
        ]
        labels = {
            "company": "Company",
            "title": "Draft title",
            "currency": "Currency",
            "discount": "Discount",
            "contact_name": "Primary contact name",
            "contact_email": "Primary contact email",
            "summary_md": "Executive Summary (Markdown)",
        }
        widgets = {
            "company": forms.Select(attrs={"required": "required", "id": "id_company"}),
            "title": forms.TextInput(attrs={"required": "required"}),
            "currency": forms.TextInput(attrs={"maxlength": 8}),
            "discount": forms.Select(),
            "contact_name": forms.TextInput(attrs={"id": "id_contact_name"}),
            "contact_email": forms.EmailInput(attrs={"id": "id_contact_email"}),
            "summary_md": forms.Textarea(attrs={"rows": 6}),
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

def client_queryset():
    role_val = None
    try:
        role_val = getattr(User.Roles, "CLIENT", None) or getattr(User.Roles, "CLIENT".upper(), None)
    except Exception:
        pass
    filters = {"is_staff": False}
    if role_val:
        filters["role"] = role_val
    else:
        # Fallback if your custom user doesn't expose Roles enum
        filters["role"] = "CLIENT"
    return User.objects.filter(**filters).order_by("first_name", "last_name", "email")

class AddViewerForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=client_queryset(),
        label="Client",
        help_text="Give this client access to view this proposal."
    )

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
    ProposalDraft, DraftNote,
    formset=BaseDraftNoteFS,
    fields=["subject", "body_md", "sort_order"],
    extra=1,
    can_delete=True,
    widgets={
        "body_md": forms.Textarea(attrs={"rows": 4}),
    },
)

# -------------------------------------------
# Item Inline
# -------------------------------------------
DraftItemInlineFormSet = inlineformset_factory(
    parent_model=ProposalDraft,
    model=DraftItem,
    fields=["hours", "quantity", "sort_order"],
    extra=0,
    can_delete=True,
    widgets={
        "hours": forms.NumberInput(attrs={"step": "0.50", "min": "0"}),
        "quantity": forms.NumberInput(attrs={"step": "1", "min": "0"}),
    },
)