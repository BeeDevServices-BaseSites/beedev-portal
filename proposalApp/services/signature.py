from __future__ import annotations
from io import BytesIO
from hashlib import sha256
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

from PIL import Image, ImageDraw, ImageFont  # pip install Pillow

DEFAULT_FONT_PATH = "assets/fonts/GreatVibes-Regular.ttf"  # put a script .ttf in your repo/static

def render_signature_png(name: str, *, font_path: str = DEFAULT_FONT_PATH, size_px=(900, 260)) -> bytes:
    name = (name or "").strip() or " "
    img = Image.new("RGBA", size_px, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, 120)
    except Exception:
        font = ImageFont.load_default()
    # fit to canvas
    bbox = draw.textbbox((0, 0), name, font=font)
    while bbox[2] - bbox[0] > size_px[0] - 60 and getattr(font, "size", 26) > 26:
        font = ImageFont.truetype(font.path, font.size - 6) if hasattr(font, "path") else font
        bbox = draw.textbbox((0, 0), name, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size_px[0] - w) // 2
    y = (size_px[1] - h) // 2
    # subtle shadow + main text
    draw.text((x+1, y+1), name, font=font, fill=(0, 0, 0, 90))
    draw.text((x, y), name, font=font, fill=(10, 10, 10, 255))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def save_signature_image_for_proposal(proposal, name: str) -> str:
    raw = render_signature_png(name)
    digest = sha256(raw).hexdigest()[:16]
    fname = f"signatures/proposal/{proposal.id or 'new'}/{slugify(name) or 'signature'}-{digest}.png"
    default_storage.save(fname, ContentFile(raw))
    return fname

def hash_current_document(proposal) -> str:
    """
    Prefer hashing the *PDF bytes* if present (binds signature to the exact file the signer saw).
    Fallback to a structured hash of fields if no PDF exists yet.
    """
    try:
        if getattr(proposal, "pdf", None) and proposal.pdf:
            with proposal.pdf.open("rb") as f:
                import hashlib
                return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        pass

    # fallback: hash material fields + line items
    import json, hashlib
    basis = {
        "title": proposal.title,
        "company_id": proposal.company_id,
        "amount_subtotal": str(proposal.amount_subtotal or 0),
        "discount_total":  str(proposal.discount_total  or 0),
        "amount_total":    str(proposal.amount_total    or 0),
        "deposit_amount":  str(proposal.deposit_amount  or 0),
        "summary_md":      proposal.summary_md or "",
        "payment_terms_md": proposal.payment_terms_md or "",
        "legal_terms_md":   proposal.legal_terms_md or "",
        "items": [
            {"name": li.name, "hours": str(li.hours), "qty": str(li.quantity), "line_total": str(li.line_total)}
            for li in proposal.line_items.order_by("sort_order", "id")
        ],
    }
    blob = json.dumps(basis, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
