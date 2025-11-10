# proposalApp/services/display.py
from decimal import Decimal
from ..models import Discount, ProposalDraft
from ..models import ProposalAppliedDiscount  # type hints only (optional)
from . import __init__  # no-op, keeps package importable
from ..models import Proposal  # type hints only (optional)
from decimal import ROUND_HALF_UP

def q2(val):
    if val is None:
        val = Decimal("0")
    return Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_display_totals(
    *,
    subtotal: Decimal,
    deposit_type: str,
    deposit_value: Decimal,
    discount_kind: str | None,
    discount_value: Decimal | None,
    discount_requires_verification: bool,
    is_discount_verified: bool,
):
    """
    Returns a dict for templates with:
      subtotal, discount_applied, discount_amount, post_total,
      hyp_discount_amount, hyp_total, deposit_due
    """
    subtotal = q2(subtotal or 0)

    # Deposit is always from pre-discount subtotal
    if deposit_type == ProposalDraft.DepositType.PERCENT:
        deposit_due = q2(subtotal * (deposit_value or 0) / Decimal("100"))
    elif deposit_type == ProposalDraft.DepositType.FIXED:
        deposit_due = q2(deposit_value or 0)
    else:
        deposit_due = Decimal("0.00")

    # Actual (applied) discount
    applied = False
    discount_amount = Decimal("0.00")
    if discount_kind:
        if (not discount_requires_verification) or is_discount_verified:
            applied = True
            if discount_kind == Discount.Kind.PERCENT:
                discount_amount = q2(subtotal * (discount_value or 0) / Decimal("100"))
            else:
                discount_amount = q2(discount_value or 0)

    post_total = q2(subtotal - discount_amount)

    # Hypothetical (for the parentheses when pending)
    hyp_amount = Decimal("0.00")
    if discount_kind:
        if discount_kind == Discount.Kind.PERCENT:
            hyp_amount = q2(subtotal * (discount_value or 0) / Decimal("100"))
        else:
            hyp_amount = q2(discount_value or 0)
    hyp_total = q2(subtotal - hyp_amount)

    # Cap deposit to post_total
    if deposit_due > post_total:
        deposit_due = post_total

    return {
        "subtotal": subtotal,
        "discount_applied": applied,
        "discount_amount": discount_amount,
        "post_total": post_total,
        "hyp_discount_amount": hyp_amount,
        "hyp_total": hyp_total,
        "deposit_due": deposit_due,
    }

# Convenience wrappers so views can just pass the object:

def display_for_draft(draft: ProposalDraft):
    disc_kind = draft.discount.kind if draft.discount else None
    disc_val  = draft.discount.value if draft.discount else None
    requires  = bool(getattr(draft.discount, "requires_verification", False)) if draft.discount else False
    verified  = bool(getattr(draft, "is_discount_verified", False))
    return compute_display_totals(
        subtotal=draft.subtotal,
        deposit_type=draft.deposit_type,
        deposit_value=draft.deposit_value,
        discount_kind=disc_kind,
        discount_value=disc_val,
        discount_requires_verification=requires,
        is_discount_verified=verified,
    )

def display_for_proposal(prop):
    subtotal = q2(prop.amount_subtotal or 0)

    # Deposit from pre-discount subtotal
    if prop.deposit_type == ProposalDraft.DepositType.PERCENT:
        deposit_due = q2(subtotal * (prop.deposit_value or 0) / Decimal("100"))
    elif prop.deposit_type == ProposalDraft.DepositType.FIXED:
        deposit_due = q2(prop.deposit_value or 0)
    else:
        deposit_due = Decimal("0.00")

    applied_discount_sum = Decimal("0.00")
    hypothetical_discount_sum = Decimal("0.00")
    details = []

    for ad in prop.applied_discounts.order_by("sort_order", "id"):
        # actual applied
        applied_discount_sum += q2(ad.amount_applied or 0)
        # hypothetical (as-if verified/active)
        if ad.kind == Discount.Kind.PERCENT:
            hyp = q2(subtotal * (ad.value or 0) / Decimal("100"))
        else:
            hyp = q2(ad.value or 0)
        hypothetical_discount_sum += hyp

        details.append({
            "name": ad.name,
            "code": ad.discount_code,
            "kind": ad.kind,
            "value": ad.value,
            "requires_verification": bool(getattr(ad, "requires_verification", False)),
            "pending": bool(getattr(ad, "pending_verification", False)),
            "applied_amount": q2(ad.amount_applied or 0),
            "hypothetical_amount": hyp,
        })

    post_total = q2(subtotal - applied_discount_sum)
    hyp_total  = q2(subtotal - hypothetical_discount_sum)

    # cap deposit by post-discount total
    if deposit_due > post_total:
        deposit_due = post_total

    return {
        "subtotal": subtotal,
        "discount_applied": applied_discount_sum > 0,
        "discount_amount": applied_discount_sum,
        "post_total": post_total,
        "hyp_discount_amount": hypothetical_discount_sum,
        "hyp_total": hyp_total,
        "deposit_due": deposit_due,
        "discount_details": details,  # for line-by-line rendering if you want
    }

