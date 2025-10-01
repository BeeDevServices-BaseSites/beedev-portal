# proposalApp/messenger.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_proposal(proposal, recipient_emails, signing_url, subject=None, body_text=None, **kwargs):
    """
    Called by Proposal.mark_sent().
    - recipient_emails: list[str]
    - signing_url: absolute URL to public view (already built)
    """
    if not recipient_emails:
        return

    context = {
        "proposal": proposal,
        "company": proposal.company,
        "signing_url": signing_url,
    }

    subj = subject or f"Proposal: {proposal.title}"
    text = body_text or render_to_string("proposals/email.txt", context)
    html = render_to_string("proposals/email.html", context)

    msg = EmailMultiAlternatives(subj, text, to=recipient_emails)
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)
