# ticketApp Audit

## Purpose

Handles client/staff tickets, requests, issue messages, attachments, watchers, and ticket event history.

This app is the closest existing piece to the Portal 2.0 request/issue tracking system.

---

# models.py

## Keep

### Ticket
- Company relationship.
- Customer user.
- Created by.
- Assigned to.
- Public ticket key.
- Subject.
- Description.
- Status.
- Priority.
- Category.
- Watchers.
- Created/updated tracking.
- Open/closed helper.

### TicketMessage
- Message/comment thread per ticket.
- Staff/client author distinction.
- Internal-only notes.
- Client message protection.
- Last client reply tracking.

### TicketAttachment
- File attachment support.
- File type validation.
- File size validation.
- Upload path organization.

### TicketEvent
- Ticket activity history.
- Event kinds.
- Actor tracking.
- JSON data for flexible history.

---

## Edit Later

### Ticket Relationship

Currently tickets only connect to:

- Company

Portal 2.0 needs tickets/requests/issues to optionally connect to:

- Company
- Project
- Phase
- Sprint

Likely future fields:

- project
- phase
- sprint

This is especially important for clients like Novel eShelf with:
- Author Launch
- Reader Platform
- Mobile App
- Phase-based launches
- Sprint work

### Category

Current categories:

- Content
- Bug
- Feature/Request
- Billing
- Other

Review later against Portal 2.0 request types.

Potential future types:

- Bug
- Feature Request
- Content Change
- Design Change
- DevOps
- Question
- Internal Task
- Support
- Public Issue

### Source

Portal 2.0 needs a way to track where the request came from.

Potential source field:

- Public Form
- Client Portal
- Email
- Discord
- Meeting
- Staff
- Status Site

This is critical because the current pain point is that requests come from emails and Discord and get lost.

### Visibility

Ticket messages have `is_internal`, which is good.

Ticket itself may also need visibility flags later:

- client_visible
- public_visible
- internal_only

### Public Reporting

Need to support public issue reports from the status site.

This may require:
- public reporter name
- public reporter email
- public source metadata
- optional no-login submission flow

### Statuses

Current statuses are good for support tickets.

Review whether Portal 2.0 needs:
- Backlog
- Review
- Blocked
- Waiting on Client
- Complete

---

## Pause

Nothing major.

This app should not be paused.

Some advanced parts can wait:

- Attachment UI
- Watcher notifications
- SLA/reporting
- Advanced event automation

---

## Remove

None currently.

---

## Portal 2.0 Notes

ticketApp should become one of the main Portal 2.0 apps.

Recommended future role:
- Public issue intake
- Client issue/request intake
- Staff-created requests from email/Discord/meetings
- Internal-only tasks/notes
- Client-visible request tracking
- Request history and comments

The main missing piece is project structure.

Portal 2.0 needs tickets/requests to connect to:
Company → Project → Phase → Sprint

This app is not something to scrap. It is the foundation of the new request system.

---

# admin.py

## Keep

### TicketAdmin
- Strong admin list view.
- Useful search fields.
- Useful filters for status, priority, and category.
- Assignment support.
- Watchers support.
- Quick status actions.
- Assign-to-me action.
- Attachment count link.
- Attention flag for high/urgent open tickets.

### TicketMessageInline
- Useful for threaded ticket conversations.
- Supports staff/client messages.
- Supports internal-only messages.

### TicketAttachmentInline
- Useful for message-level attachments.

### TicketEventInline
- Useful for history/activity tracking.

### TicketMessageAdmin
- Useful for managing individual ticket messages.

### TicketAttachmentAdmin
- Useful for managing uploaded attachments.

## Edit Later

### Permissions
- Current permissions use Django groups: Owner, Admin, HR.
- Other apps use `User.role`.
- Portal 2.0 should standardize permissions across apps.

### Staff Access
- Only Owner/Admin can add/change tickets in admin.
- Later, regular staff may need limited ticket update abilities.

### Project/Phase/Sprint Fields
- Admin should eventually support filtering by:
  - project
  - phase
  - sprint

### Public/Client Intake
- Admin is staff-side only.
- Portal 2.0 still needs frontend/API flows for:
  - public issue reports
  - client-created requests
  - staff-created requests from email/Discord

## Pause

- Advanced attachment management.
- Advanced watcher notifications.
- SLA/reporting.

## Remove

None currently.

## Notes

ticketApp admin is already useful and should stay.

The admin supports internal ticket management well, but Portal 2.0 needs API/Vite flows for public, client, and staff request intake.

This app is a core part of Portal 2.0 Phase 1.

# urls / views

## Current Structure

- Views are already in a folder.
- URLs are currently split into two files.

## Edit Later

- Convert URL files into a `urls/` folder structure.
- Match the pattern being used in the Novel eShelf project.
- Separate public, client, staff, and API routes.

## Suggested Future URL Structure

ticketApp/
  urls/
    __init__.py
    public.py
    client.py
    staff.py
    api.py

## Portal 2.0 Notes

ticketApp should eventually support separate flows for:
- Public issue reporting
- Client portal requests
- Staff-created/internal requests
- API endpoints for the Vite frontend

---

# views/staff.py

## Keep

- Staff ticket dashboard concept.
- Staff-only permission check.
- Ticket list concept.

## Edit Later

- Convert this Django template view into an API endpoint for Vite/React.
- Add filtering instead of `Ticket.objects.all()`.
- Add separate views/endpoints for:
  - assigned to me
  - unassigned tickets
  - high priority tickets
  - waiting on client
  - recently updated
  - client-visible requests
- Add project/phase/sprint filters after project structure exists.
- Use `@login_required` if this remains a Django view.

## Archive / Replace

- `ticket_staff/staff_ticket_home.html`

This will likely become a Vite/React page.

## Notes

Current staff view is very minimal.

The concept is worth keeping, but Portal 2.0 needs a stronger staff dashboard focused on:
- what is new
- what is urgent
- what is blocked
- what is waiting on client
- what is assigned to each team member