# prospectApp Audit

## Purpose

Handles prospective clients, consultation tracking, prospect notes, conversion to companies, onboarding creation, and portal invite creation.

---

# models.py

## Keep

### Prospect
- Basic prospect/contact record.
- Status tracking.
- Contact information.
- Website URL.
- External consultation sheet URL.
- Notes and tags.
- Follow-up tracking.
- Created/updated user tracking.

### ProspectNote
- Useful log of notes against a prospect.
- Supports pinned notes.
- Supports markdown-style note body.

### Conversion Helpers
- `create_or_update_company`
- `ensure_client_onboarding_list`
- `create_portal_invite`

These are useful because they connect prospect flow into company/client onboarding.

---

## Edit Later

### Status Flow

Current statuses are useful:

- New
- Consultation Pending
- Consultation Complete
- Proposal Sent
- Won
- Closed/Lost

Review later against the BeeDev sales process.

### Company Conversion

Review fields copied into Company.

Note:
Some `fields_to_update` names may need review later because they appear to use names like `contact_name` / `contact_email`, while the Company fields are `primary_contact_name` / `primary_contact_email`.

Do not fix during audit.

### Onboarding Dependency

This app reaches into `onboardingApp`.

That is okay, but since onboarding is Phase 2/later, prospect conversion should not block Portal 2.0 Phase 1.

---

## Pause

- Full CRM workflow.
- Follow-up dashboard.
- Prospect onboarding automation.
- Proposal pipeline.

Useful later, but not required for the first project/request tracking rebuild.

---

## Remove

None currently.

---

## Portal 2.0 Notes

prospectApp is useful but should remain separate from active client/project work.

Recommended Portal 2.0 role:
- Track potential clients before they become companies.
- Convert won prospects into Company records.
- Create portal invites.
- Optionally create onboarding lists later.

Do not use prospectApp as the main client/project dashboard.

---

# admin.py

## Keep

### ProspectAdmin
- Useful admin interface for managing prospects.
- Good search fields.
- Good status and country filters.
- Tracks created_by and updated_by.
- Includes prospect notes inline.
- Supports follow-up fields.

### ProspectNoteInline
- Useful for quick prospect notes.
- Keeps notes tied to the prospect record.

### convert_to_company admin action
- Very useful.
- Supports converting prospects into companies.
- Marks prospect as WON.
- Reuses the model helper instead of duplicating conversion logic.

## Edit Later

- Review whether prospect conversion should also create:
  - company member
  - portal invite
  - onboarding list
- Review the note inline save logic later if needed.

## Pause

- Full CRM dashboard.
- Prospect follow-up automation.
- Sales pipeline views.

Useful later, not required for Portal 2.0 Phase 1.

## Remove

None.

## Notes

The admin is solid and should stay.

ProspectApp can remain a lightweight CRM area while Portal 2.0 focuses on active client/project/request tracking.