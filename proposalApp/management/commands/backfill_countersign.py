from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from proposalApp.models import Proposal, proposal_pdf_upload_to
from proposalApp.services import pdf_stamp

User = get_user_model()

class Command(BaseCommand):
    help = "Append countersign certificate to existing proposal PDFs"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, required=True, help="User id to record as countersigner")
        parser.add_argument("--only-missing", action="store_true", help="Only proposals without countersign")
        parser.add_argument("--mode", choices=["append", "overlay"], default="append")

    def handle(self, *args, **opts):
        user = User.objects.get(pk=opts["user_id"])
        qs = Proposal.objects.all()
        if opts["only_missing"]:
            qs = qs.filter(countersigned_at__isnull=True)

        n = 0
        for p in qs.iterator():
            if opts["only_missing"] and p.countersigned_at:
                continue
            if not p.pdf:
                continue

            if not p.countersigned_at:
                p.countersigned_at = timezone.now()
                p.countersigned_by = user
                p.countersign_required = False
                p.save(update_fields=["countersigned_at","countersigned_by","countersign_required","updated_at"])

            if opts["mode"] == "overlay":
                fname, data = pdf_stamp.overlay_signature_on_last_page(p, user)
            else:
                fname, data = pdf_stamp.append_certificate(p, user)

            storage_name = proposal_pdf_upload_to(p, fname)
            default_storage.save(storage_name, ContentFile(data))
            p.pdf.name = storage_name
            p.save(update_fields=["pdf"])
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {n} proposal(s)."))
