# proposalApp/forms.py
from decimal import Decimal
from django import forms
from companyApp.models import Company
from .models import Discount

class NewDraftForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label="Company"
    )
    title = forms.CharField(max_length=200, label="Draft title")
    currency = forms.CharField(max_length=8, initial="USD", label="Currency")
    discount = forms.ModelChoiceField(
        queryset=Discount.objects.filter(is_active=True),
        required=False,
        label="Discount"
    )
    contact_name = forms.CharField(max_length=160, required=False, label="Primary contact name")
    contact_email = forms.EmailField(required=False, label="Primary contact email")

    def clean(self):
        cleaned = super().clean()
        # If employee leaves contact fields blank, we’ll fill from company in the view.
        return cleaned


class DraftNoteForm(forms.Form):
    subject = forms.CharField(max_length=160, required=False, label="Section title")
    body_md = forms.CharField(
        required=False,
        label="Details (Markdown)",
        widget=forms.Textarea(attrs={"rows": 4})
    )
