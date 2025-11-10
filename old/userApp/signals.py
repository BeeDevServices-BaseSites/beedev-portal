# userApp/signals.py
from __future__ import annotations
from django.db.models.signals import post_migrate, post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from django.contrib.auth.models import Group
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import ClientProfile, EmployeeProfile
from proposalApp.models import ProposalAccountInvite, ProposalEvent
from companyApp.models import CompanyMembership

ROLE_GROUPS = ["Owner", "Admin", "Employee", "Client"]
AUX_GROUPS  = ["HR"]

User = get_user_model()

@receiver(post_migrate)
def ensure_default_groups(sender, **kwargs):
    for name in ROLE_GROUPS + AUX_GROUPS:
        Group.objects.get_or_create(name=name)

@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def cache_old_role(sender, instance: User, **kwargs):
    instance._old_role = None
    if instance.pk:
        try:
            instance._old_role = sender.objects.get(pk=instance.pk).role
        except sender.DoesNotExist:
            pass

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def sync_role_to_group_and_profiles(sender, instance: User, created, **kwargs):
    # --- role -> group sync (no HR here)
    role_to_group = {
        "OWNER": "Owner",
        "ADMIN": "Admin",
        "EMPLOYEE": "Employee",
        "CLIENT": "Client",
    }
    target = role_to_group.get(instance.role)
    if target:
        role_group_qs = Group.objects.filter(name__in=ROLE_GROUPS)
        instance.groups.remove(*role_group_qs)
        g, _ = Group.objects.get_or_create(name=target)
        instance.groups.add(g)

    # --- profiles (optional; keep if you're using both profiles)
    old = getattr(instance, "_old_role", None)
    is_client      = (instance.role == User.Roles.CLIENT)
    is_companyside = (instance.role in (User.Roles.EMPLOYEE, User.Roles.ADMIN, User.Roles.OWNER))

    if created or old != instance.role:
        if is_client:
            ClientProfile.objects.get_or_create(user=instance)
            EmployeeProfile.objects.filter(user=instance).delete()
        elif is_companyside:
            EmployeeProfile.objects.get_or_create(user=instance)
            ClientProfile.objects.filter(user=instance).delete()

    # --- is_staff auto-manage (role OR HR group)
    in_hr = instance.groups.filter(name="HR").exists()
    desired_staff = is_companyside or in_hr
    if instance.is_staff != desired_staff:
        # Use update() to avoid recursive save signals
        instance.__class__.objects.filter(pk=instance.pk).update(is_staff=desired_staff)

@receiver(m2m_changed, sender=User.groups.through)
def ensure_staff_follows_hr_group(sender, instance: User, action, reverse, model, pk_set, **kwargs):
    # When HR group membership changes, keep is_staff in sync
    if action in {"post_add", "post_remove", "post_clear"}:
        company_roles = {getattr(instance.Roles, "EMPLOYEE", "EMPLOYEE"),
                         getattr(instance.Roles, "ADMIN", "ADMIN"),
                         getattr(instance.Roles, "OWNER", "OWNER")}
        in_hr = instance.groups.filter(name="HR").exists()
        desired_staff = (instance.role in company_roles) or in_hr
        if instance.is_staff != desired_staff:
            instance.__class__.objects.filter(pk=instance.pk).update(is_staff=desired_staff)


@receiver(user_logged_in)
def link_company_from_pending_invite(sender, request, user, **kwargs):
    """
    When a user logs in and we previously stashed a proposal invite token in
    session (from the invite flow), attach them to the invite's company and
    mark the invite used.

    This lets one User (same email) be linked to multiple companies.
    """
    # Pull & clear the token so we don't re-run.
    token = None
    try:
        token = request.session.pop("pending_invite_token", None)
    except Exception:
        token = None

    if not token:
        return

    try:
        inv = ProposalAccountInvite.objects.select_related("company", "proposal").get(token=token)
    except ProposalAccountInvite.DoesNotExist:
        return

    # Guard: if the invite is already used/expired, do nothing
    if inv.is_used or inv.is_expired:
        return

    with transaction.atomic():
        # Link user ↔ company (idempotent)
        CompanyMembership.objects.get_or_create(
            company=inv.company,
            user=user,
            defaults={"is_active": True},
        )

        # Mark invite used
        inv.mark_used(user=user, save=True)

        # Optional: write an event on the proposal for audit
        try:
            if inv.proposal_id:
                ProposalEvent.objects.create(
                    proposal=inv.proposal,
                    kind=ProposalEvent.Kind.UPDATED,
                    actor=None,
                    data={"invite": {"token": inv.token, "used_by": user.email, "via": "login"}},
                )
        except Exception:
            # Never block login on event logging
            pass