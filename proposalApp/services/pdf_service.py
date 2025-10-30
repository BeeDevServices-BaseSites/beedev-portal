# proposalApp/pdf_service.py
import os
from io import BytesIO
from decimal import Decimal
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.staticfiles import finders
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
from weasyprint import HTML, CSS
from django.templatetags.static import static as static_url

try:
    import markdown as _md
    def _md_html(text: str) -> str:
        return _md.markdown(text or "", extensions=["extra", "sane_lists", "tables", "fenced_code"])
except Exception:
    def _md_html(text: str) -> str:
        return (text or "").replace("\n", "<br>")

COMPANY_SIGNATURE_STAMP_ENABLED = bool(getattr(settings, "COMPANY_SIGNATURE_STAMP_ENABLED", False))

DOMAIN_TEXT = getattr(settings, "PROPOSAL_DOMAIN_TEXT",
    "DNS Handling (included in 1st year) and Domain Renewals and record upkeep (optional for subsequent years or as needed)")
HOSTING_FALLBACK_TEXT = getattr(settings, "PROPOSAL_HOSTING_FALLBACK_TEXT",
    "$20 (monthly) or $200 (annually)")

def _company_signature_ctx(proposal) -> dict:
    info = {"signed": False, "name": None, "signed_at": None}
    try:
        if getattr(proposal, "countersigned_by_id", None) and proposal.countersigned_at:
            name = (
                getattr(proposal.countersigned_by, "get_full_name", lambda: "")()
                or getattr(proposal.countersigned_by, "email", None)
                or "Authorized Signer"
            )
            info.update({
                "signed": True,
                "name": name,
                "signed_at": timezone.localtime(proposal.countersigned_at),
            })
    except Exception:
        pass
    return info

def _client_signature_ctx(proposal) -> dict:
    info = {"signed": False, "name": None, "signed_at": None}
    try:
        if getattr(proposal, "contact_name", None) and proposal.signed_at:
            info.update({
                "signed": True,
                "name": proposal.contact_name,
                "signed_at": timezone.localtime(proposal.signed_at),
            })
    except Exception:
        pass
    return info

def apply_company_signature_stamp(pdf_bytes: bytes, proposal) -> bytes:
    try:
        if not pdf_bytes:
            return pdf_bytes or b""
        if not getattr(proposal, "countersigned_by_id", None) or not proposal.countersigned_at:
            return pdf_bytes

        reader = PdfReader(BytesIO(pdf_bytes))
        if not reader.pages:
            return pdf_bytes

        last = reader.pages[-1]
        w = float(last.mediabox.right) - float(last.mediabox.left)
        h = float(last.mediabox.top) - float(last.mediabox.bottom)

        overlay_buf = BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(w, h))

        font_name = "Helvetica-Oblique"
        ttf_path = getattr(settings, "COMPANY_SIGNATURE_TTF", None)
        if ttf_path:
            try:
                pdfmetrics.registerFont(TTFont("CompanyScript", str(ttf_path)))
                font_name = "CompanyScript"
            except Exception:
                pass

        signer = (
            getattr(proposal.countersigned_by, "get_full_name", lambda: "")()
            or getattr(proposal.countersigned_by, "email", None)
            or "Authorized Signer"
        )
        ts = timezone.localtime(proposal.countersigned_at).strftime("%b %d, %Y %I:%M %p %Z")

        pad = 0.6 * inch
        box_h = 1.4 * inch

        # Draw box
        c.setLineWidth(1)
        c.rect(pad, pad, w - 2 * pad, box_h, stroke=1, fill=0)

        # Big signature-style name
        c.setFont(font_name, 24)
        c.drawString(pad + 0.2 * inch, pad + box_h - 0.5 * inch, signer)

        # Labels
        c.setFont("Helvetica", 10)
        c.drawString(pad + 0.2 * inch, pad + box_h - 0.85 * inch, "BeeDev Services — Company Countersignature")
        c.drawString(pad + 0.2 * inch, pad + 0.35 * inch, f"Date: {ts}  •  Becomes fully executed upon client signature.")

        c.save()
        overlay_reader = PdfReader(BytesIO(overlay_buf.getvalue()))

        # Merge overlay onto last page
        last.merge_page(overlay_reader.pages[0])

        # Write new PDF
        out = BytesIO()
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.write(out)
        return out.getvalue()

    except Exception:
        # Fail-safe: if anything goes wrong, return the original bytes
        return pdf_bytes or b""

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


    print(proposal)

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
        "company_signature": _company_signature_ctx(proposal),
        "client_signature": _client_signature_ctx(proposal),
    }

def _abs_url(request, path: str) -> str:
    """
    Build an absolute HTTP(S) URL for 'path' (which can already be absolute).
    Falls back to settings.SITE_URL if request is None.
    """
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = (request.build_absolute_uri("/") if request else getattr(settings, "SITE_URL", "").rstrip("/") + "/")
    return base.rstrip("/") + "/" + path.lstrip("/")

def _css_list_with_fallback(css_static_paths: list[str], request):
    """
    Try to load CSS via HTTP(S) absolute URLs first. If prod renderer cannot reach
    the host or you prefer not to make HTTP calls, we also add filesystem CSS via
    Django staticfiles finders as a fallback.
    """
    css_objs = []

    # Primary: absolute HTTP(S) URLs for CSS
    for rel in css_static_paths:
        url = _abs_url(request, static_url(rel))
        css_objs.append(CSS(url=url))

    # Fallback: filesystem CSS (works even if HTTP is blocked)
    for rel in css_static_paths:
        fs = finders.find(rel)  # e.g. "css/proposal-pdf.css" → "/app/static/css/proposal-pdf.css"
        if fs:
            css_objs.append(CSS(filename=fs))
    return css_objs

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

    if not base_url:
        base_url = (request.build_absolute_uri("/") if request else getattr(settings, "SITE_URL", None)) or "http://localhost/"

    css_paths = css_static_paths or ["css/proposal-pdf.css"]
    css_list = _css_list_with_fallback(css_paths, request)

    pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf(stylesheets=css_list)
    if COMPANY_SIGNATURE_STAMP_ENABLED:
        pdf_bytes = apply_company_signature_stamp(pdf_bytes, proposal)

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
