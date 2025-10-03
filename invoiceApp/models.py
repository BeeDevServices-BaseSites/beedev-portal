# invoiceApp/models.py
import os, uuid, datetime, secrets
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

# ---------- Validators / helpers ----------
PDF_VALIDATOR = FileExtensionValidator(["pdf"])
MAX_PDF_BYTES = 15 * 1024 * 1024

def _validate_size(file, max_bytes, label="file"):
    if file and file.size and file.size > max_bytes:
        raise ValidationError(f"{label} too large (> {max_bytes//1024//1024}MB).")

def invoice_pdf_upload_to(instance, filename):
    # MEDIA: invoices/<company>/<YYYY/MM>/<invoice-no or id>-<uuid>.pdf
    today = datetime.date.today()
    comp_bucket = getattr(getattr(instance, "company", None), "slug", None) or "company"
    ident = instance.number or f"inv-{instance.pk or 'new'}"
    return f"invoices/{comp_bucket}/{today.year}/{today.month:02d}/{ident}-{uuid.uuid4().hex}.pdf"


# =======================================================================
#                              INVOICE
# =======================================================================
class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT    = "DRAFT",    "Draft"
        SENT     = "SENT",     "Sent"
        PARTIAL  = "PARTIAL",  "Partially Paid"
        PAID     = "PAID",     "Paid"
        VOID     = "VOID",     "Void"

    company         = models.ForeignKey("companyApp.Company", on_delete=models.CASCADE, related_name="invoices")
    proposal        = models.ForeignKey("proposalApp.Proposal", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")


    customer_user   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="customer_invoices")
    customer_contact = models.ForeignKey("companyApp.CompanyContact", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")

    number      = models.CharField(max_length=40, unique=True, blank=True)
    currency    = models.CharField(max_length=8, default="USD")
    issue_date  = models.DateField(default=datetime.date.today)
    due_date    = models.DateField(null=True, blank=True)

    subtotal       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_total      = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total          = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    minimum_due    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    amount_paid    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status         = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    view_token     = models.CharField(max_length=64, unique=True, blank=True)

    pdf            = models.FileField(upload_to=invoice_pdf_upload_to, blank=True, null=True, validators=[PDF_VALIDATOR])
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices_created")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="InvoiceViewer",
        related_name="invoices_shared_with",
        blank=True,
    )

    stripe_customer_id          = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_invoice_id           = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_checkout_session_id  = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_payment_intent_id    = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_hosted_invoice_url   = models.URLField(blank=True)
    stripe_status               = models.CharField(max_length=32, blank=True)  # e.g., 'draft','open','paid','void','uncollectible'

    def __str__(self):
        return f"Invoice {self.number} — {self.company.name}"

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["number"]),
            models.Index(fields=["company", "customer_user"]),
        ]

    def __str__(self):
        return self.number or f"Invoice #{self.pk}"

    @property
    def balance_due(self) -> Decimal:
        return (self.total or Decimal("0.00")) - (self.amount_paid or Decimal("0.00"))

    def recalc_totals(self, *, save=True):
        sub = sum((li.subtotal or Decimal("0.00")) for li in self.line_items.all())
        disc = sum((ad.amount_applied or Decimal("0.00")) for ad in self.applied_discounts.all())
        self.subtotal = sub
        self.discount_total = disc
        base = (self.subtotal - self.discount_total).quantize(Decimal("0.01"))
        self.total = base + (self.tax_total or Decimal("0.00"))
        if save:
            self.save(update_fields=["subtotal", "discount_total", "total", "updated_at"])
        return self.total

    def refresh_status_from_payments(self, *, save=True):
        paid = sum((p.amount or Decimal("0.00")) for p in self.payments.all())
        self.amount_paid = paid
        new_status = self.Status.DRAFT if self.status == self.Status.DRAFT else (
            self.Status.PAID if self.balance_due <= Decimal("0.00")
            else self.Status.PARTIAL if paid > Decimal("0.00")
            else self.Status.SENT
        )
        self.status = new_status
        if save:
            self.save(update_fields=["amount_paid", "status", "updated_at"])

    def save(self, *args, **kwargs):
        if not self.view_token:
            self.view_token = secrets.token_urlsafe(32)
        if not self.number:
            base = timezone.now().strftime("%Y%m%d")
            self.number = f"INV-{base}-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

    @classmethod
    def from_proposal(cls, proposal, *, created_by=None, due_date=None, customer_user=None):
        if customer_user is None and getattr(proposal, "contact", None):
            customer_user = getattr(proposal.contact, "user", None)

        inv = cls.objects.create(
            company=proposal.company,
            proposal=proposal,
            customer_user=customer_user,
            customer_contact=getattr(proposal, "contact", None),
            currency=proposal.currency,
            due_date=due_date,
            minimum_due=proposal.deposit_amount or Decimal("0.00"),
            tax_total=proposal.amount_tax or Decimal("0.00"),
            created_by=created_by,
            status=cls.Status.SENT,
        )
        for li in proposal.line_items.all().order_by("sort_order", "pk"):
            InvoiceLineItem.objects.create(
                invoice=inv,
                sort_order=li.sort_order,
                name=li.name,
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                subtotal=li.subtotal,
            )
        for ad in proposal.applied_discounts.all().order_by("sort_order", "id"):
            InvoiceAppliedDiscount.objects.create(
                invoice=inv,
                discount_code=ad.discount_code,
                name=ad.name,
                kind=ad.kind,
                value=ad.value,
                amount_applied=ad.amount_applied,
                sort_order=ad.sort_order,
            )
        inv.recalc_totals(save=True)
        return inv

# =======================================================================
#                          INVOICE LINE ITEMS
# =======================================================================
class InvoiceLineItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    sort_order  = models.PositiveIntegerField(default=0)
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity    = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ("sort_order", "pk")

    def __str__(self):
        return f"{self.name} ({self.quantity} @ {self.unit_price})"

# =======================================================================
#                          INVOICE DISCOUNT
# =======================================================================
class InvoiceAppliedDiscount(models.Model):
    invoice       = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="applied_discounts")
    discount_code = models.SlugField(max_length=40)
    name          = models.CharField(max_length=120)
    kind          = models.CharField(max_length=10, choices=[("PERCENT","Percent"),("FIXED","Fixed amount")])
    value         = models.DecimalField(max_digits=10, decimal_places=2)
    amount_applied= models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sort_order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

# =======================================================================
#                             PAYMENT
# =======================================================================
class Payment(models.Model):
    class Method(models.TextChoices):
        CARD   = "CARD",   "Card"
        ACH    = "ACH",    "ACH / Bank"
        CHECK  = "CHECK",  "Check"
        CASH   = "CASH",   "Cash"
        STRIPE = "STRIPE", "Stripe"
        OTHER  = "OTHER",  "Other"

    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    method      = models.CharField(max_length=10, choices=Method.choices, default=Method.CARD)
    reference   = models.CharField(max_length=120, blank=True)

    payer_user  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments_made")

    received_at = models.DateTimeField(default=timezone.now)
    notes       = models.TextField(blank=True)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments_recorded")
    updated_at = models.DateTimeField(auto_now=True)

    stripe_payment_intent_id   = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_charge_id           = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_payment_method_id   = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_receipt_url         = models.URLField(blank=True)
    gateway_payload            = models.JSONField(blank=True, default=dict)
    gateway_status             = models.CharField(max_length=32, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-received_at", "id")

    def __str__(self):
        return f"Payment {self.amount} on {self.invoice}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.refresh_status_from_payments(save=True)

class InvoiceViewer(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="allowed_viewers")
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="allowed_invoices")

    class Meta:
        unique_together = [("invoice", "user")]
        indexes = [models.Index(fields=["invoice", "user"])]

    def __str__(self):
        return f"{self.user} can view {self.invoice}"