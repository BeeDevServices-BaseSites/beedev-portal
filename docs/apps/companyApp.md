# companyApp Audit

## Purpose

Handles companies/clients, company members, client-facing links, updates, invitations, and several document-related records.

---

# models.py

## Keep

### Company
- Core client/company record.
- Slug support.
- Primary contact details.
- Website and logo support.
- Basic company status.
- Created/updated tracking.

### CompanyMember
- Connects users to companies.
- Supports client contacts and staff members.
- Important for client portal access.

### CompanyLinkType
- Defines reusable link categories.
- Useful for links like GitHub, Figma, preview site, live site, status page, maintenance page, assets folder, etc.

### CompanyLink
- Stores company/client-specific links.
- Supports client-visible vs internal-only links.
- Very useful for Portal 2.0.

### CompanyUpdateLog
- Useful for posting client/project updates.
- Can support client-visible updates later.

### PortalInvite
- Supports client invitation flow.
- Connects company, email, token, expiration, and usage status.

---

## Edit Later

### Company Status Fields

Review the status system.

Current fields include:

- `status`
- `pipeline_status`
- `work_status`
- `project_phase`

These may overlap with future project, phase, sprint, and issue tracking.

Likely direction:

- Keep `Company.status` for company/client lifecycle.
- Move project-specific status and phase tracking into `projectApp`.
- Review whether `pipeline_status` belongs with prospects/CRM.
- Review whether `work_status` should become project/request/task status instead.

### Company / Project Relationship

Portal 2.0 should likely treat Company as the parent record and Project as the work container.

Example:

- Company: Novel eShelf
  - Project: Author Launch
  - Project: Reader Platform
  - Project: Mobile App
  - Project: Maintenance / Support

---

## Pause

### ProposalDocument
- Useful later.
- Not required for Portal 2.0 Phase 1.

### RoadMap
- Useful later.
- Not required for Portal 2.0 Phase 1.

### Invoice
- Useful later.
- Not required for Portal 2.0 Phase 1.

### Agreement
- Useful later for signed contracts and SOWs.
- Not required for Portal 2.0 Phase 1.

---

## Remove

None currently.

---

## Portal 2.0 Notes

companyApp remains a core app.

The strongest reusable pieces are:

- Company
- CompanyMember
- CompanyLinkType
- CompanyLink
- CompanyUpdateLog
- PortalInvite

The main concern is that Company currently carries some project-tracking fields that may belong in projectApp after the rebuild.

Portal 2.0 should use Company as the client/business container, not as the full project tracker.

---

# admin.py

## Keep

### CompanyAdmin
- Strong company management interface.
- Company member management.
- Logo management.
- Contact management.
- Consultation/prospect linkage.
- Audit tracking.

### CompanyMemberInline
- Useful way to manage client contacts and staff relationships.

### CompanyUpdateLogAdmin
- Useful for client-visible updates.
- Likely reusable in Portal 2.0.

### PortalInviteAdmin
- Supports client invitation workflow.
- Complements userApp invitation flow.

### CompanyLinkType Admin
- Simple and useful.
- Supports reusable link categories.

---

## Edit Later

### CompanyAdmin Inlines

Currently includes:

- ProposalDocument
- RoadMap
- Agreement
- Invoice

These may eventually be moved into dedicated sections of the portal rather than being managed primarily through CompanyAdmin.

### Permission Helpers

Review consistency with:

- userApp permissions
- future API permissions
- Portal 2.0 role system

---

## Pause

### ProposalDocumentAdmin

Useful later.

### RoadMapAdmin

Useful later.

### InvoiceAdmin

Useful later.

### AgreementAdmin

Useful later.

These support business operations but are not required for Portal 2.0 Phase 1.

---

## Remove

None currently.

---

## Notes

The admin structure is significantly stronger than expected.

Recommendation:
Continue using Django Admin as the internal administration tool while building the Vite frontend.

No major redesign required.

The admin already provides effective management for:
- Companies
- Members
- Updates
- Invites

which are all Portal 2.0 core concepts.