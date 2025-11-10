# proposalApp/services/pdf_stamp.py
from __future__ import annotations
from io import BytesIO
from datetime import datetime
from hashlib import sha256

from django.utils import timezone
from django.core.files.base import ContentFile

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from PyPDF2 import PdfReader, PdfWriter

def _first_page_size(pdf_bytes: bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    if not reader.pages:
        return letter
    mb = reader.pages[0].mediabox
    # PyPDF2 points are strings in some versions; cast to float
    w = float(mb.right) - float(mb.left)
    h = float(mb.top) - float(mb.bottom)
    return (w, h)

def _render_certificate_page(proposal, signer_user, original_pdf: bytes) -> bytes:
    buf = BytesIO()
    size = _first_page_size(original_pdf) if original_pdf else letter
    c = canvas.Canvas(buf, pagesize=size)

    now = timezone.now()
    signer_name = getattr(signer_user, "get_full_name", lambda: "")() or str(signer_user)
    signer_email = getattr(signer_user, "email", "") or ""
    company_name = proposal.company.name if proposal.company_id else "—"
    title = proposal.title or f"Proposal #{proposal.pk}"
    sha = sha256(original_pdf or b"").hexdigest()

    margin = 0.85 * inch
    y = size[1] - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Company Countersignature Certificate")
    y -= 0.4 * inch

    c.setFont("Helvetica", 11)
    def line(label, value):
        nonlocal y
        c.drawString(margin, y, f"{label}:")
        c.drawString(margin + 2.2*inch, y, str(value))
        y -= 0.28 * inch

    line("Proposal", title)
    line("Company", company_name)
    line("Proposal ID", proposal.pk or "—")
    if getattr(proposal, "code", None):
        line("Proposal Code", proposal.code)

    # countersign info
    c.line(margin, y, size[0]-margin, y); y -= 0.18*inch
    line("Countersigned by", signer_name)
    if signer_email:
        line("Signer Email", signer_email)
    line("Countersigned at", now.strftime("%Y-%m-%d %H:%M:%S %Z"))
    c.line(margin, y, size[0]-margin, y); y -= 0.18*inch

    # integrity statement
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(margin, y, "This page certifies BeeDev’s company countersignature for the attached proposal.")
    y -= 0.22*inch
    c.drawString(margin, y, "Original PDF SHA-256:")
    y -= 0.22*inch
    c.setFont("Courier", 9)
    c.drawString(margin, y, sha or "(not available)")

    c.showPage()
    c.save()
    return buf.getvalue()

def _render_overlay_signature(proposal, signer_user, target_page_size):
    """Transparent overlay to place on the last page (bottom area)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=target_page_size)
    w, h = target_page_size
    pad = 0.6*inch
    box_h = 1.3*inch
    y0 = pad
    x0 = pad
    # signature box
    c.setLineWidth(1)
    c.rect(x0, y0, w-2*pad, box_h, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0 + 0.2*inch, y0 + box_h - 0.35*inch, "BeeDev Services — Company Countersignature")

    c.setFont("Helvetica", 10)
    name = getattr(signer_user, "get_full_name", lambda: "")() or str(signer_user)
    email = getattr(signer_user, "email", "") or ""
    ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    c.drawString(x0 + 0.2*inch, y0 + box_h - 0.65*inch, f"Signed by: {name}  {('('+email+')') if email else ''}")
    c.drawString(x0 + 0.2*inch, y0 + box_h - 0.95*inch, f"Date: {ts}")
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(x0 + 0.2*inch, y0 + 0.3*inch, "Becomes fully executed upon client signature.")
    c.save()
    return buf.getvalue()

def append_certificate(proposal, signer_user) -> tuple[str, bytes]:
    """
    Returns (filename, pdf_bytes) with an extra cert page appended.
    """
    base_bytes = b""
    if getattr(proposal, "pdf", None) and proposal.pdf:
        proposal.pdf.open("rb")
        base_bytes = proposal.pdf.read()
        proposal.pdf.close()

    cert = _render_certificate_page(proposal, signer_user, base_bytes)

    writer = PdfWriter()
    if base_bytes:
        reader = PdfReader(BytesIO(base_bytes))
        for p in reader.pages:
            writer.add_page(p)
    # append certificate
    writer.append_pages_from_reader(PdfReader(BytesIO(cert)))

    out = BytesIO()
    writer.write(out)
    return (f"Proposal-{proposal.pk}-countersigned.pdf", out.getvalue())

def overlay_signature_on_last_page(proposal, signer_user) -> tuple[str, bytes]:
    """
    Returns (filename, pdf_bytes) with a signature box overlaid onto the last page.
    """
    if not getattr(proposal, "pdf", None) or not proposal.pdf:
        raise ValueError("No base PDF to overlay.")

    proposal.pdf.open("rb")
    base_bytes = proposal.pdf.read()
    proposal.pdf.close()

    reader = PdfReader(BytesIO(base_bytes))
    if not reader.pages:
        raise ValueError("PDF has no pages.")
    last = reader.pages[-1]
    size = (float(last.mediabox.right) - float(last.mediabox.left),
            float(last.mediabox.top) - float(last.mediabox.bottom))

    overlay_bytes = _render_overlay_signature(proposal, signer_user, size)
    overlay_reader = PdfReader(BytesIO(overlay_bytes))
    last.merge_page(overlay_reader.pages[0])

    out = BytesIO()
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    writer.write(out)
    return (f"Proposal-{proposal.pk}-countersigned.pdf", out.getvalue())
