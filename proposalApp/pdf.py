# proposalApp/pdf.py
import os
from io import BytesIO
from decimal import Decimal
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.staticfiles import finders

from weasyprint import HTML, CSS

try:
    import markdown as _md
    def _md_html(text: str) -> str:
        return _md.markdown(text or "", extensions=["extra", "sane_lists", "tables", "fenced_code"])
except Exception:
    def _md_html(text: str) -> str:
        return (text or "").replace("\n", "<br>")

DOMAIN_TEXT = getattr(settings, "PROPOSAL_DOMAIN_TEXT",
    "DNS Handling (included in 1st year) and Domain Renewals and record upkeep (optional for subsequent years or as needed)")
HOSTING_FALLBACK_TEXT = getattr(settings, "PROPOSAL_HOSTING_FALLBACK_TEXT",
    "$20 (monthly) or $200 (annually)")

def _static_css(paths):
    css_objs = []
    for p in paths:
        fp = finders.find(p)
        if fp:
            css_objs.append(CSS(filename=fp))
    return css_objs

def _proposal_basename(proposal):
    company_slug = getattr(proposal.company, "slug", None) or slugify(str(proposal.company or "company"))
    return f"{company_slug}-proposal-{proposal.pk}"

def _build_filename(proposal, overwrite: bool, storage):
    dt = getattr(proposal, "created_at", None) or timezone.now()
    subdir = os.path.join("proposals", f"{dt:%Y}", f"{dt:%m}")
    base = _proposal_basename(proposal)
    if overwrite:
        return subdir, f"{base}.pdf"
    v = 1
    while True:
        name = f"{base}-v{v:03}.pdf"
        path = os.path.join(subdir, name)
        if not storage.exists(path):
            return subdir, name
        v += 1

def _hosting_line(proposal) -> str | None:
    try:
        items = getattr(proposal, "line_items").all()
    except Exception:
        items = []
    for li in items:
        name = (li.name or "").lower()
        if "host" in name:
            return f"{li.name} — Qty {li.quantity:g}, Hours {li.hours:g}"
    return None

def _valid_until(proposal):
    if getattr(proposal, "converted_from_id", None) and proposal.converted_from:
        return proposal.converted_from.valid_until_effective
    base = getattr(proposal, "created_at", None) or timezone.now()
    return (base + timezone.timedelta(days=30)).date()

def _pdf_context(proposal) -> dict:
    company = proposal.company
    proposal_date = (proposal.created_at or timezone.now()).date()
    total = getattr(proposal, "amount_total", Decimal("0.00"))


    summary_md = ""
    try:
        summary_md = getattr(getattr(proposal, "summary", None), "body_md", "") or ""
    except Exception:
        pass
    summary_html = _md_html(summary_md)


    notes_blocks = []
    for n in getattr(proposal, "notes", []).all() if hasattr(proposal, "notes") else []:
        if getattr(n, "is_visible_to_client", True):
            notes_blocks.append({
                "subject": n.subject or "Notes",
                "body_html": _md_html(n.body_md or ""),
            })


    hosting_auto = _hosting_line(proposal)
    hosting_text = hosting_auto or HOSTING_FALLBACK_TEXT


    valid_until = _valid_until(proposal)
    days_valid = (valid_until - proposal_date).days
    deposit = getattr(proposal, "deposit_amount", Decimal("0.00"))
    remaining = getattr(proposal, "remaining_due", Decimal("0.00"))
    hours_total = getattr(proposal, "hours_total", Decimal("0.00"))

    return {
        "company_name": str(company),
        "proposal_date": proposal_date,
        "quote_total": total,
        "domain_text": DOMAIN_TEXT,
        "hosting_text": hosting_text,
        "summary_html": summary_html,
        "notes_blocks": notes_blocks,
        "valid_until": valid_until,
        "valid_days": days_valid,
        "deposit_amount": deposit,
        "remaining_due": remaining,
        "hours_total": hours_total,
    }

def generate_proposal_pdf(
    proposal,
    *,
    request=None,
    base_url: str | None = None,
    overwrite: bool = True,
    delete_old: bool = False,
    template_name: str = "proposal_staff/pdf/proposal.html",
    css_static_paths: list[str] | None = None,
    context_extra: dict | None = None,
) -> str:
    from django.core.files.storage import default_storage
    storage = default_storage

    ctx = {
        "proposal": proposal,
        "company": proposal.company,
        "now": timezone.now(),
    }
    ctx.update(_pdf_context(proposal))
    if context_extra:
        ctx.update(context_extra)

    html_string = render_to_string(template_name, ctx, request=request)

    css_list = _static_css(css_static_paths or ["css/proposal-pdf.css"])

    pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf(stylesheets=css_list)

    subdir, filename = _build_filename(proposal, overwrite=overwrite, storage=storage)
    storage_path = os.path.join(subdir, filename)

    if overwrite and delete_old and getattr(proposal, "pdf", None) and proposal.pdf:
        try:
            if storage.exists(proposal.pdf.name):
                storage.delete(proposal.pdf.name)
        except Exception:
            pass

    saved_name = storage.save(storage_path, ContentFile(pdf_bytes))
    try:
        proposal.pdf.save(os.path.basename(saved_name), ContentFile(pdf_bytes), save=False)
    except Exception:
        proposal.pdf.name = saved_name
    finally:
        proposal.save(update_fields=["pdf"])

    return saved_name
