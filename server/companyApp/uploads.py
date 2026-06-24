# companyApp/uploads.py
import os

def _company_pk(instance):
    company = getattr(instance, "company", None)
    return getattr(company, "pk", None)

def proposals_upload_to(instance, filename):
    pk = _company_pk(instance)
    return os.path.join("companies", str(pk or "unknown"), "proposals", filename)

def roadmaps_upload_to(instance, filename):
    pk = _company_pk(instance)
    return os.path.join("companies", str(pk or "unknown"), "roadmaps", filename)

def invoices_upload_to(instance, filename):
    pk = _company_pk(instance)
    return os.path.join("companies", str(pk or "unknown"), "invoices", filename)

def agreements_signed_upload_to(instance, filename):
    pk = _company_pk(instance)
    return os.path.join("companies", str(pk or "unknown"), "agreements", "signed", filename)

def agreements_source_upload_to(instance, filename):
    pk = _company_pk(instance)
    return os.path.join("companies", str(pk or "unknown"), "agreements", "source", filename)
