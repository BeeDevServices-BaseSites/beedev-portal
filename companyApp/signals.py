# companyApp/signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import ProposalDocument, RoadMap, Invoice, Agreement


def _delete_filefield(instance, field_name: str):
    f = getattr(instance, field_name, None)
    if f and getattr(f, "name", ""):
        try:
            f.delete(save=False)
        except Exception:
            pass


@receiver(post_delete, sender=ProposalDocument)
def delete_proposal_file(sender, instance, **kwargs):
    _delete_filefield(instance, "file")


@receiver(post_delete, sender=RoadMap)
def delete_roadmap_file(sender, instance, **kwargs):
    _delete_filefield(instance, "file")

@receiver(post_delete, sender=Invoice)
def delete_invoice_file(sender, instance, **kwargs):
    _delete_filefield(instance, "file")

@receiver(post_delete, sender=Agreement)
def delete_agreement_file(sender, instance, **kwargs):
    _delete_filefield(instance, "file_signed")
    _delete_filefield(instance, "file_source")