# invoiceApp/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from proposalApp.models import Proposal
from companyApp.models import CompanyMembership
from .models import Invoice

User = get_user_model()

KIND_DEPOSIT   = "DEPOSIT"
KIND_BALANCE   = "BALANCE"
KIND_ONE_OFF   = "ONE_OFF"
KIND_RECURRING = "RECURRING"

KIND_CHOICES = [
    (KIND_DEPOSIT,   "Deposit"),
    (KIND_BALANCE,   "Balance"),
    (KIND_ONE_OFF,   "One-off"),
    (KIND_RECURRING, "Recurring"),
]

class CreateInvoiceFromProposalForm(forms.Form):
    proposal = forms.ModelChoiceField(
        queryset=Proposal.objects.none(),
        label="Signed Proposal",
        help_text="Only signed proposals you can access will be listed.",
    )
    kind = forms.ChoiceField(
        choices=KIND_CHOICES,
        initial=KIND_DEPOSIT,
        label="Invoice Type",
    )
    due_date = forms.DateField(
        required=False,
        label="Due Date (optional)",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    customer_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Customer User (optional override)",
        help_text="Leave blank to auto-use the proposal’s contact user (if any).",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Proposal.objects.filter(signed_at__isnull=False).order_by("-created_at")

        if user and not getattr(user, "is_superuser", False):
            if getattr(user, "is_staff", False):
                company_ids = CompanyMembership.objects.filter(
                    user=user, is_active=True
                ).values_list("company_id", flat=True)
                qs = qs.filter(Q(company_id__in=company_ids) | Q(allowed_viewers__user=user)).distinct()
            else:
                qs = qs.filter(allowed_viewers__user=user).distinct()

        self.fields["proposal"].queryset = qs

        cust_qs = User.objects.all().order_by("email")

        if self.is_bound:
            try:
                data_p = self.data.get(self.add_prefix("proposal")) or self.initial.get("proposal")
                if data_p:
                    p = qs.filter(pk=data_p).first()
                    if p:
                        company_user_ids = CompanyMembership.objects.filter(
                            company=p.company, is_active=True
                        ).values_list("user_id", flat=True)

                        allowed_user_ids = p.allowed_viewers.values_list("user_id", flat=True)

                        contact_user_id = getattr(getattr(p, "contact", None), "user_id", None)

                        id_filter = list(company_user_ids) + list(allowed_user_ids)
                        if contact_user_id:
                            id_filter.append(contact_user_id)

                        cust_qs = User.objects.filter(id__in=set(id_filter)).order_by("email")
            except Exception:
                pass

        self.fields["customer_user"].queryset = cust_qs

    def clean_proposal(self):
        p = self.cleaned_data["proposal"]
        if not p.signed_at:
            raise forms.ValidationError("This proposal is not signed yet.")
        return p

    def clean_customer_user(self):
        user = self.cleaned_data.get("customer_user")
        p = self.cleaned_data.get("proposal")
        if not user or not p:
            return user

        in_company = CompanyMembership.objects.filter(company=p.company, user=user, is_active=True).exists()
        is_allowed = p.allowed_viewers.filter(user=user).exists()
        is_contact_user = getattr(getattr(p, "contact", None), "user_id", None) == user.id

        if not (in_company or is_allowed or is_contact_user):
            raise forms.ValidationError("Selected user is not associated with this proposal’s company.")
        return user

    def clean(self):
        cleaned = super().clean()
        p = cleaned.get("proposal")
        kind = cleaned.get("kind")
        if not p or not kind:
            return cleaned

        if kind == KIND_DEPOSIT and (p.deposit_amount or 0) <= 0:
            self.add_error("kind", "This proposal has no deposit amount configured.")

        if kind == KIND_DEPOSIT:
            existing_dep = Invoice.objects.filter(
                proposal=p,
                minimum_due__gt=0
            ).exclude(status=Invoice.Status.VOID).exists()
            if existing_dep:
                self.add_error("proposal", "A deposit invoice already exists for this proposal.")

        if kind == KIND_BALANCE and (p.remaining_due or 0) <= 0:
            self.add_error("kind", "This proposal has no remaining balance to invoice.")

        return cleaned

    def selected_kind(self):
        return self.cleaned_data.get("kind")
