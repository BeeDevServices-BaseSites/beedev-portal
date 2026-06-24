# companyApp/forms.py

from django import forms
from .models import Company, CompanyUpdateLog, CompanyLink


class UpdateCompanyInfoForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "name",
            "primary_contact_email",
            "phone",
            "website",
            "address_line1",
            "address_line2",
            "city",
            "state_region",
            "postal_code",
        )


class UpdateCompanyStatusForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "status",
            "pipeline_status",
            "work_status",
        )


class UpdateCompanyProjectPhaseForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "project_phase",
        )

class CompanyUpdateLogForm(forms.ModelForm):
    class Meta:
        model = CompanyUpdateLog
        fields = ("title", "body", "pinned", "visible_to_client")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 5}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"].required = False
        self.fields["body"].required = False

class CompanyLinkForm(forms.ModelForm):
    class Meta:
        model = CompanyLink
        fields = ["link_type", "title", "url", "notes", "visible_to_client", "is_active"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }