# proposalApp/email_backend.py
from django.core.mail.backends.smtp import EmailBackend
import ssl, certifi

class GmailEmailBackend(EmailBackend):
    """
    SMTP backend that uses certifi's CA bundle so TLS verification succeeds.
    """
    def _get_ssl_context(self):
        return ssl.create_default_context(cafile=certifi.where())
