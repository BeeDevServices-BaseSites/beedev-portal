# onboardingApp Audit

## Purpose

Handles reusable onboarding checklists for staff and clients.

---

# models.py

## Keep

### TimeStamped
- Useful shared abstract timestamp model.
- Could possibly move to a shared/common app later, but no need now.

### OnboardingTaskTemplate
- Reusable master task/checklist template.
- Supports staff onboarding and client onboarding.
- Supports ordering.
- Supports active/inactive templates.
- Supports required resources.

### OnboardingList
- Creates onboarding checklists for either staff users or companies.
- Supports client onboarding and staff onboarding.
- Tracks visibility, management-only status, completion, and archive status.
- Can populate checklist items from templates.
- Has useful progress helpers:
  - total_items
  - completed_items
  - percent_complete
  - refresh_completion_status

### OnboardingListItem
- Individual checklist item.
- Supports completion tracking.
- Supports completed_by.
- Supports required resource checks.
- Supports notes.

---

## Edit Later

### Relationship to Portal 2.0 Projects

Review whether some onboarding logic overlaps with project/task templates.

Portal 2.0 will likely have:

- Project templates
- Phase templates
- Sprint/task templates
- Issue/request tracking

Onboarding should stay focused on onboarding, not become the general project task system.

### Visibility Rules

Review:

- `visible_to_subject`
- `management_only`

These are useful, but will need clear API permissions when moving to Vite/React.

### Naming

Consider whether "subject" should become clearer later:

- visible_to_subject
- visible_to_client_or_staff
- visible_to_assigned_user

No change now.

---

## Pause

- Staff onboarding UI.
- Client onboarding UI.
- Resource upload requirements.

These are useful later, but not required for Portal 2.0 Phase 1 unless client onboarding becomes part of initial portal access.

---

## Remove

None currently.

---

## Portal 2.0 Notes

onboardingApp is reusable as a checklist system.

Recommended role in Portal 2.0:
- Use for staff onboarding.
- Use for client onboarding.
- Do not use as the main project/task tracker.
- Keep project work in projectApp/issues/tickets.

This app should remain separate from the main project request system.

---

# admin.py

## Keep

### OnboardingTaskTemplateAdmin
- Useful for managing reusable onboarding task templates.
- Supports staff/client template separation.
- Supports active/inactive templates.
- Supports ordering.

### OnboardingListAdmin
- Useful for managing generated onboarding checklists.
- Supports staff and company/client onboarding.
- Includes inline checklist items.
- Automatically populates checklist items from templates when a new list is created.

### OnboardingListItemInline
- Useful for editing checklist items directly from the onboarding list.
- Supports completion tracking.
- Supports required resource/resource added tracking.

### OnboardingListItemAdmin
- Useful for direct checklist item management.
- Search and filters are helpful.

## Edit Later

### Permission Helpers
- Current permissions use Django groups: Owner, Admin, HR.
- Other apps use `User.role`.
- Portal 2.0 should standardize permissions across apps.

### HR Role
- HR-related permissions may not be needed in Portal 2.0 Phase 1.
- Review later when staff/intern onboarding becomes active again.

## Pause

- Staff onboarding workflows.
- HR/admin onboarding permissions.
- Resource-required checklist workflows.

These are useful later but not needed for the first request/project tracking rebuild.

## Remove

None currently.

## Notes

The admin is useful and should stay.

The main issue is permission style inconsistency:
- onboardingApp uses groups.
- userApp/companyApp mostly use `User.role`.

This does not need to be fixed now, but should be documented for later cleanup.