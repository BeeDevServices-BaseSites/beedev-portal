# templates Audit

## Purpose

Django template files used by the portal for page rendering, emails, admin customization, shared layouts, and error pages.

---

## Folders

### admin/

Status: Review Later

Notes:
- Contains Django admin customizations.
- Django Admin will remain part of Portal 2.0.
- Many of these templates will likely remain.
- Review individually during implementation.

### block/

Status: Review Later

Notes:
- Shared template blocks and reusable layout components.
- May be replaced by React components during Vite migration.
- Review before removal.

### emails/

Status: Likely Keep

Notes:
- Email templates remain useful regardless of frontend framework.
- Invitation emails, notifications, and client communications will still be needed.
- Review and modernize later.

### errors/

Status: Partial Keep

Notes:
- Error pages remain useful.
- May be converted to React pages later.
- Keep until replacement exists.

### base.html

Status: Likely Archive Later

Notes:
- Current master Django template layout.
- Vite frontend will eventually replace most responsibilities.
- Keep until migration is complete.

---

## Audit Conclusion

Templates should not be deeply audited at this stage.

Portal 2.0 Priority:
Low

Recommendation:
Review folder-by-folder during frontend migration.

Important:
Do not remove templates until Vite/React replacements exist.

Expected Outcome:

Keep:
- admin templates
- email templates
- some error templates

Likely Retire:
- most page-rendering templates
- shared layout templates once React is primary