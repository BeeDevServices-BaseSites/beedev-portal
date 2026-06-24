# core Audit

## Purpose

Shared portal infrastructure, including email helpers, context helpers, and Django template utilities.

---

## emails/portal_invites

### Keep

- Portal invite email concept.
- Likely still needed for client onboarding.

### Edit Later

- Review after `PortalInvite` workflow is finalized.
- Make sure invite links point to the Vite frontend route or correct Django API flow.

---

## utils/context.py

### Pause / Likely Archive

- Likely supports Django template context.
- May not be needed once Vite/React handles page layout.

### Edit Later

- Check whether any non-template logic is reusable before archiving.

---

## templatetags/page_title.py

### Archive Later

- Likely only supports Django templates.
- Not needed in React/Vite frontend.

---

## templatetags/user_extras.py

### Archive Later

- Likely only supports Django templates.
- Review first in case it contains reusable role/display helpers.

---

## Audit Conclusion

core is mostly small shared infrastructure.

Recommendation:
- Keep emails.
- Review utils.
- Archive most templatetags after Vite migration.