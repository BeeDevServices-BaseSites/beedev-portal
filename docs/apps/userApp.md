# userApp Audit

## Purpose

Handles authentication, users, roles, client profiles, employee profiles, invitations, and staff documents.

---

# models.py

## Keep

### User
- Custom User model
- Role system
- Email uniqueness
- Avatar helper

### ClientProfile
- Contact information
- Profile image support

### EmployeeProfile
- Employee information
- Discord handle
- Internal notes

## Edit Later

- Review role helper methods
- Review relationship between ClientProfile and Company records

## Pause

### StaffDocument
- Contracts
- Payout statements
- Staff file management

## Remove

- None

---

# urls.py

## Keep

- Login route concept
- Logout route concept
- Post-login redirect
- Invite acceptance flow

## Edit Later

- Convert page routes to API endpoints
- Review authentication flow for Vite frontend

## Archive / Replace

- staff/
- employee/
- staff/clients/
- staff/team/
- staff/profile/

These are likely to become React routes backed by API endpoints.

## Notes

- No forms.py found.
- Views are organized as a folder and need separate review.

# views/

## Files Found

- client.py
- profile.py
- root.py
- staff.py

## Review Order

1. root.py
2. client.py
3. staff.py
4. profile.py

## Initial Notes

- Views are split by responsibility, which is good.
- Most template-rendering views will likely be edited or replaced when Vite/React takes over the frontend.
- Any login, invite, role redirect, or permission logic may still be reusable.

---

# views/root.py

## Purpose

Handles portal login, post-login routing, staff dashboard, employee redirect, and basic client dashboard.

## Keep

- `PortalLogin` concept
- `post_login` concept
- Role-based redirect idea
- Staff dashboard metrics concept
- Client dashboard concept
- Separation between staff and client landing areas

## Edit Later

- `PortalLogin` currently renders a Django template. This may need to become API/token-based auth or be replaced by the Vite login page.
- `post_login` should be reviewed once Vite routing is planned.
- Staff/client redirects should eventually point to frontend routes or API responses instead of Django template pages.
- Dashboard queries may be reusable, but should likely move into API views/services.
- Staff permission helpers should be reviewed with Portal 2.0 role rules.
- Imports include several apps that may change or be paused: `prospectApp`, `ticketApp`, `onboardingApp`.

## Archive / Replace

- `staff_home` template render:
  - `userApp/staff/staff_home.html`
- `client_home` template render:
  - `userApp/client/client_home.html`

These pages will likely become Vite/React pages.

## Pause / Revisit

- Prospect dashboard widgets
- Onboarding dashboard widgets

These may still be useful, but Portal 2.0 phase 1 should focus on clients, projects, issues/requests, phases, and sprints.

## Notes

- `staff_home` already shows the type of dashboard Portal 2.0 needs, but the metrics should shift from prospects/onboarding toward:
  - open client issues
  - untriaged requests
  - blocked tasks
  - waiting on client
  - current phase/sprint work
  - assigned-to-me items
- `client_home` is currently very simple and should be rebuilt around client projects and visible requests.

# views/client.py

## Purpose

Handles client invitation acceptance.

## Keep

- Invite acceptance concept.
- Token-based invitation flow.
- Client onboarding entry point.

## Edit Later

- Complete invite workflow.
- Determine how invited users create accounts.
- Connect invite acceptance to company and project access.
- Decide whether onboarding happens in Django API or Vite frontend.

## Archive / Replace

- None.

## Notes

This is currently a placeholder.

The concept is important and should remain in Portal 2.0 because client invitations will still be needed.

Potential future flow:

Staff creates client contact
    ↓
Invitation email sent
    ↓
Client accepts invitation
    ↓
Client creates password
    ↓
Client profile created
    ↓
Client linked to company
    ↓
Client gains access to assigned projects

# views/staff.py

## Purpose

Handles staff-only pages for viewing clients/prospects and team admin.

## Keep

- Staff permission helper concept.
- Upper management permission helper concept.
- Staff-only client/contact overview concept.
- Team admin concept.

## Edit Later

- Convert staff pages to API endpoints for the Vite frontend.
- Rework staff permissions into a reusable permission system.
- Replace template rendering with API responses.
- Review how `CompanyMember` should control client/staff access.
- Rename or split `view_all_clients` because it currently handles clients, prospects, won prospects, lost prospects, and onboarding.

## Pause

- Prospect-heavy workflow.
- Lost/won prospect display.
- Client onboarding list display.
- Team admin page.

These may still be useful later, but Portal 2.0 Phase 1 should focus on active clients, projects, issues/requests, phases, and sprints.

## Archive / Replace

- `userApp/staff/view_all_contacts.html`
- `userApp/staff/team_home.html`

These will likely become Vite/React pages.

## Notes

This file has useful staff/admin access patterns, but it is still shaped around Portal 1.0 CRM/admin pages.

For Portal 2.0, the staff view should shift toward:
- all active clients
- active projects
- untriaged issues
- requests waiting on staff
- items waiting on client
- current sprint work
- blocked tasks

# views/profile.py

## Purpose

Handles staff profile display and eventually client profile views.

## Keep

- Staff profile concept.
- EmployeeProfile connection.
- Auto-create profile behavior with `get_or_create`.
- Staff-only permission check concept.

## Edit Later

- Convert staff profile page to API endpoint for Vite/React.
- Decide whether profiles should be read-only, editable, or editable by role.
- Reuse shared permission helpers instead of repeating `_allowed_staff`.
- Add or rebuild client profile functionality later.

## Archive / Replace

- `userApp/staff/view_staff_profile.html`

This will likely become a Vite/React page.

## Pause

- Client profile functions are not built yet.
- Profile editing can wait unless needed for launch.

## Notes

This file is small and reusable conceptually. The profile model can stay, but the display/edit experience should move to the React frontend later.

# admin.py

## Purpose

Provides Django admin management for users, client profiles, employee profiles, and staff documents.

## Keep

### CustomUserAdmin
- Custom user administration
- Role-based visibility
- Role-based permissions
- Profile inline support

### ClientProfileAdmin
- Search functionality
- Filtering
- Profile image preview
- Read-only timestamps

### EmployeeProfileAdmin
- Search functionality
- Filtering
- Profile image preview
- Staff self-management restrictions

### Permission Structure

The overall permission philosophy is solid:

Owner
    Full access

Admin
    Elevated access

Staff
    Limited access

Client
    No admin access

## Edit Later

### Permission Helpers

Review consistency between:

- is_owner()
- is_staff_role()
- role helper methods in models.py

Potentially move to a shared permission module.

### Profile Administration

Review whether profile editing should eventually happen in the Vite frontend instead of relying on Django Admin.

## Pause

### StaffDocumentAdmin

Useful later for:

- Contracts
- Payout statements
- Staff files

Not required for Portal 2.0 Phase 1.

## Remove

None.

## Notes

The Django admin remains valuable even after the Vite frontend is built.

Recommendation:
Keep Django Admin as the internal administration tool while building the client/staff experience in React.

No major redesign needed.