# IMPORTANT

Portal 2.0 is NOT a rewrite.

Goal:
Reuse as much of Portal Lite as possible.

Expected Reuse:
75-85%

Primary Changes:
- Replace Django templates with Vite/React
- Expand ticketApp into request tracking
- Introduce Project → Phase → Sprint structure
- Retain Django Admin for internal administration

## userApp

Status: Complete

Recommendation:
Keep and Modernize

Portal 2.0 Impact:
Low

Notes:
- Backend models largely reusable
- Admin structure largely reusable
- Role system reusable
- Invitation workflow unfinished but worth keeping
- Frontend views should migrate to Vite
- StaffDocument feature moved to later phase

## announceApp

Status: Complete

Recommendation:
Keep

Portal 2.0 Impact:
Very Low

Notes:
- Self-contained app.
- Useful for staff/client announcements.
- Useful for release notes.
- No major redesign required.
- No Portal 2.0 blockers.

## companyApp

Status: Complete

Recommendation:
Keep and Modernize

Portal 2.0 Impact:
Medium

Keep:
- Company
- CompanyMember
- CompanyLinkType
- CompanyLink
- CompanyUpdateLog
- PortalInvite

Pause:
- ProposalDocument
- RoadMap
- Invoice
- Agreement

Notes:
- Company remains a core Portal 2.0 model.
- Admin interface is already strong.
- Company currently contains some project-tracking concepts that should be reviewed after projectApp audit.

## core

Status: Reviewed

Recommendation:
Keep Email Helpers, Review Utils, Archive Template Tags Later

Portal 2.0 Impact:
Low

Notes:
- Portal invite email flow is likely reusable.
- Context utilities and template tags are tied to Django templates and may not be needed after Vite migration.

## onboardingApp

Status: Complete

Recommendation:
Keep, but Phase 2 Supporting Feature

Portal 2.0 Impact:
Low to Medium

Notes:
- Strong reusable onboarding checklist system.
- Admin is usable.
- Should not become the main project/task tracker.
- Permission style should be standardized later.
- Not required for the first project/request tracking rebuild.

## portal

Status: Complete

Recommendation:
Keep

Portal 2.0 Impact:
Very Low

## prospectApp

Status: Complete

Recommendation:
Keep, but Phase 2/CRM Feature

Portal 2.0 Impact:
Low to Medium

Notes:
- Useful prospect/CRM system.
- Admin conversion to Company is valuable.
- Prospect notes are useful.
- Not needed for the first project/request tracking rebuild.

## static

Status: Deferred

Recommendation:
Review During Frontend Migration

Portal 2.0 Impact:
Low

Notes:
- Django admin assets likely remain.
- Many template-related assets may be retired later.
- Review folder-by-folder during Vite migration.

## templates

Status: Deferred

Recommendation:
Review During Frontend Migration

Portal 2.0 Impact:
Low

Notes:
- Django admin templates likely remain.
- Email templates likely remain.
- Most page-rendering templates will eventually be replaced by Vite/React.
- Do not remove until migration is complete.

## ticketApp

Status: Completed

Recommendation:
Keep and Expand

Portal 2.0 Impact:
High

Notes:
- This is the closest existing app to the new request/issue system.
- Ticket, messages, attachments, watchers, and events are valuable.
- Needs project/phase/sprint relationship.
- Needs source tracking for Email, Discord, Public Form, Client Portal, Meeting, and Staff.
- Should become core to Portal 2.0 Phase 1.

## Template and Static Migration Note

Do not remove app-level `templates/` or `static/` folders during the audit phase.

These files may still be useful for:
- Django Admin customization
- email templates
- error pages
- brand assets
- CSS reference
- rebuilding Vite/React components
- understanding old Portal Lite page structure

Remove or archive only after the matching Vite/React page or component exists.