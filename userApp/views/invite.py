# userApp/invite.py
from __future__ import annotations
import re
from django import forms
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, NoReverseMatch
from django.http import Http404, HttpRequest, HttpResponse
from userApp.models import User
from companyApp.models import CompanyMembership
from proposalApp.models import Proposal, ProposalAccountInvite, ProposalEvent, ProposalViewer
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist

User = get_user_model()

class InviteRegisterForm(forms.Form):
    full_name = forms.CharField(
        max_length=160,
        required=True,
        label="Your full name",
        widget=forms.TextInput(attrs={"placeholder": "Jane Doe"})
    )
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"})
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        label="Username",
        help_text="Letters, numbers, dot, underscore, hyphen."
    )
    password1 = forms.CharField(
        required=True, label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        required=True, label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms & Conditions."
    )

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        # Username handling (only if the user model actually has a username field)
        if _user_model_has_username():
            email = (data.get("email") or "").strip().lower()
            raw_username = (data.get("username") or "").strip()

            # Auto-generate from email if not provided
            if not raw_username and email:
                raw_username = _suggest_username_from_email(email)

            # Sanitize + ensure uniqueness
            if raw_username:
                sanitized = _sanitize_username(raw_username)
                # If the sanitized differs or is taken, pick a unique suggestion
                if (
                    sanitized.lower() != raw_username.lower()
                    or User.objects.filter(username__iexact=sanitized).exists()
                ):
                    sanitized = _unique_username(sanitized)
                data["username"] = sanitized
            else:
                # Last-ditch fallback
                data["username"] = _unique_username("user")

        return data

def _split_name(full_name: str) -> tuple[str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

def _redirect_to_proposal(proposal: Proposal):
    # Prefer your existing public view of a proposal; fall back to PDF; else home.
    try:
        return redirect(reverse("proposal_public:proposal_public_view", args=[proposal.sign_token]))
    except Exception:
        try:
            if proposal.pdf and proposal.pdf.url:
                return redirect(proposal.pdf.url)
        except Exception:
            pass
        return redirect("/")

def _user_model_has_username() -> bool:
    try:
        User._meta.get_field("username")
        return True
    except FieldDoesNotExist:
        return False

def _sanitize_username(base: str) -> str:
    """
    Keep letters, numbers, ., _, - ; trim and lower.
    """
    base = (base or "").strip().lower()
    base = re.sub(r"[^a-z0-9._-]+", "", base)
    return base or "user"

def _suggest_username_from_email(email: str) -> str:
    local = (email or "").split("@", 1)[0]
    return _sanitize_username(local or "user")

def _unique_username(seed: str) -> str:
    """
    Ensure the username is unique by appending a numeric suffix if needed.
    Only used if the User model actually has a 'username' field.
    """
    candidate = _sanitize_username(seed)
    if not User.objects.filter(username__iexact=candidate).exists():
        return candidate
    i = 2
    while True:
        test = f"{candidate}{i}"
        if not User.objects.filter(username__iexact=test).exists():
            return test
        i += 1

@transaction.atomic
def redeem_invite_and_register(request, token: str):
    inv = get_object_or_404(ProposalAccountInvite, token=token)
    proposal = inv.proposal

    # Basic validity guard
    if inv.is_used or inv.is_expired:
        ctx = {"proposal": proposal, "invite": inv, "invalid": True}
        return render(request, "proposals/invite_invalid.html", ctx, status=410)

    initial_email = inv.email or proposal.contact_email or ""
    initial_username = _suggest_username_from_email(initial_email) if _user_model_has_username() else ""
    if request.method == "POST":
        form = InviteRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            full_name = form.cleaned_data["full_name"].strip()
            pw = form.cleaned_data["password1"]

            # If a user already exists, nudge to login (optional: store token to bind post-login)
            existing = User.objects.filter(email__iexact=email).first()
            if existing:
                messages.error(request, "An account with this email already exists. Please log in to continue.")
                request.session["pending_invite_token"] = inv.token
                try:
                    return redirect(reverse("account_login"))
                except NoReverseMatch:
                    return _redirect_to_proposal(proposal)

            # Create user
            first_name, last_name = _split_name(full_name)
            create_kwargs = dict(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
            if _user_model_has_username():
                # Use cleaned/unique username from form
                username = form.cleaned_data.get("username") or _suggest_username_from_email(email)
                username = _unique_username(username)
                create_kwargs["username"] = username

            user = User.objects.create(**create_kwargs)
            user.set_password(pw)
            user.save(update_fields=["password"])

            # Link to company
            CompanyMembership.objects.get_or_create(
                company=inv.company,
                user=user,
                defaults={"is_active": True},
            )
            company = inv.company
            updated_fields = []
            ProposalViewer.objects.get_or_create(proposal=proposal, user=user)

            if hasattr(company, "status"):
                S = getattr(company, "Status", None)
                new_status = getattr(S, "ACTIVE", None) if S else None
                new_status = new_status or "ACTIVE"  # fallback to string if no enum
                if getattr(company, "status", None) != new_status:
                    company.status = new_status
                    updated_fields.append("status")
            
            if hasattr(company, "pipeline_status"):
                PS = getattr(company, "PipelineStatus", None)
                new_pipe = getattr(PS, "NEW", None) if PS else None
                new_pipe = new_pipe or "new"  # fallback to string if no enum
                if getattr(company, "pipeline_status", None) != new_pipe:
                    company.pipeline_status = new_pipe
                    updated_fields.append("pipeline_status")
            
            if updated_fields:
                company.save(update_fields=updated_fields)

            # Mark invite used & record event
            inv.mark_used(user=user, save=True)
            ProposalEvent.objects.create(
                proposal=proposal,
                kind=ProposalEvent.Kind.UPDATED,
                actor=None,
                data={"invite": {"token": inv.token, "used_by": user.email}}
            )

            # Log in and bounce back to proposal
            auth_login(request, user)
            messages.success(request, "Your account has been created and linked to this proposal.")
            try:
                redirect_to = reverse("userApp:client_home")
            except NoReverseMatch:
                redirect_to = "/"

            return render(request, "proposals/invite_success.html", {
                "proposal": proposal,
                "redirect_to": redirect_to,
                "delay_seconds": 3,
            })
    else:
        form_initial = {"email": initial_email}
        if _user_model_has_username():
            form_initial["username"] = initial_username
        form = InviteRegisterForm(initial=form_initial)

    ctx = {
        "proposal": proposal,
        "invite": inv,
        "form": form,
    }
    return render(request, "proposals/invite_register.html", ctx)
