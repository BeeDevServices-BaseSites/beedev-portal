from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404, redirect
from core.utils.context import base_ctx
from ..models import Invoice, InvoiceLineItem, InvoiceViewer
from proposalApp.models import Proposal
from userApp.models import User
from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_GET
from django.utils.encoding import smart_str
from django.conf import settings

from ..forms import (
    CreateInvoiceFromProposalForm,
    KIND_DEPOSIT, KIND_BALANCE, KIND_ONE_OFF, KIND_RECURRING
)

# -------------------------
# Permission helpers
# -------------------------
def _allowed_staff(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER}

def _allowed_management(u: User) -> bool:
    return u.is_active and u.role in {User.Roles.ADMIN, User.Roles.OWNER}

# -------------------------
# Staff: Landing
# -------------------------
@login_required
def invoice_home(request):
    user = request.user
    if not _allowed_management(request.user):
        raise PermissionDenied("Not allowed")
    
    invoices = Invoice.objects.all()
    unpaid = Invoice.objects.exclude(status__in=["PAID"])
    paid = Invoice.objects.filter(status="PAID")

    title = "Invoice Admin"
    ctx = {"user_obj": user, "read_only": True, "invoices": invoices, "unpaid": unpaid, "paid": paid}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "invoice_staff/invoice_home.html", ctx)

@login_required
def create_new_invoice(request):
    user = request.user
    if not _allowed_management(request.user):
        raise PermissionDenied("Not allowed")
    
    if request.method == "POST":
        form = CreateInvoiceFromProposalForm(request.POST, user=user)
        if form.is_valid():
            proposal: Proposal = form.cleaned_data["proposal"]
            kind = form.cleaned_data["kind"]
            due_date = form.cleaned_data.get("due_date")
            customer_user = form.cleaned_data.get("customer_user") or None

            try:
                with transaction.atomic():
                    if kind == KIND_DEPOSIT:
                        if Invoice.objects.filter(proposal=proposal).exclude(minimum_due=Decimal("0.00")).exists():
                            messages.error(request, "A deposit invoice already exists for this proposal.")
                            return _redirect_invoice_home()

                        inv = proposal.create_deposit_invoice(
                            actor=user,
                            due_date=due_date,
                            customer_user=customer_user,
                        )
                        if not inv:
                            messages.error(request, "This proposal has no deposit configured.")
                            return _redirect_invoice_home()

                        messages.success(request, f"Deposit invoice {inv.number} created.")
                        return _redirect_invoice_home()

                    elif kind == KIND_BALANCE:
                        if (proposal.remaining_due or Decimal("0.00")) <= Decimal("0.00"):
                            messages.error(request, "This proposal has no remaining balance to invoice.")
                            return _redirect_invoice_home()

                        if Invoice.objects.filter(proposal=proposal, minimum_due=Decimal("0.00")).exists():
                            messages.error(request, "A balance invoice already exists for this proposal.")
                            return _redirect_invoice_home()

                        rem = proposal.remaining_due or Decimal("0.00")
                        inv = Invoice.objects.create(
                            company=proposal.company,
                            proposal=proposal,
                            customer_user=customer_user or getattr(proposal, "contact", None) and getattr(proposal.contact, "user", None),
                            customer_contact=getattr(proposal, "contact", None),
                            currency=proposal.currency,
                            issue_date=None,
                            due_date=due_date,
                            subtotal=rem,
                            discount_total=Decimal("0.00"),
                            tax_total=Decimal("0.00"),
                            total=rem,
                            minimum_due=Decimal("0.00"),
                            amount_paid=Decimal("0.00"),
                            status=Invoice.Status.SENT,
                            created_by=user,
                        )
                        InvoiceLineItem.objects.create(
                            invoice=inv,
                            sort_order=0,
                            name=f"Remaining balance — {proposal.title}",
                            description=f"Balance due on signed proposal {proposal.title}",
                            quantity=Decimal("1.00"),
                            unit_price=rem,
                            subtotal=rem,
                        )
                        inv.recalc_totals(save=True)

                        messages.success(request, f"Balance invoice {inv.number} created.")
                        return _redirect_invoice_home()

                    elif kind in (KIND_ONE_OFF, KIND_RECURRING):
                        messages.error(request, "That invoice type isn’t implemented yet. Choose Deposit or Balance for now.")

            except PermissionDenied:
                raise
            except Exception as e:
                messages.error(request, f"Could not create invoice: {e!r}")

    else:
        form = CreateInvoiceFromProposalForm(user=user)

    title = "Create Invoice"
    ctx = {"user_obj": user, "read_only": True, "form": form}
    ctx.update(base_ctx(request, title=title))
    ctx["page_heading"] = title
    return render(request, "invoice_staff/create_new_invoice.html", ctx)

# -------------------------
# Small redirect helper
# -------------------------
def _redirect_invoice_home() -> HttpResponse:
    try:
        return redirect("invoiceApp:invoice_home")
    except NoReverseMatch:
        try:
            return redirect("invoice_home")
        except NoReverseMatch:
            return redirect("/")