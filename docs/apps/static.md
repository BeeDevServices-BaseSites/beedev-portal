# static Audit

## Purpose

Static assets used by the portal including branding, styling, images, and Django admin customization.

---

## Folders

### admin/

Status: Review Later

Notes:
- Contains Django admin customizations.
- Likely still needed because Django Admin will remain the internal administration interface.
- Review individual files during Portal 2.0 implementation.

### css/

Status: Review Later

Notes:
- Some CSS may be tied to Django templates.
- Vite frontend will likely replace much of this.
- Review before removal.

### images/

Status: Review Later

Notes:
- Likely contains shared BeeDev branding assets.
- Review for reusable logos, icons, and portal images.
- Do not remove until Vite frontend is complete.

### root/

Status: Review Later

Notes:
- Review contents individually.
- Determine whether files support Django templates, admin customization, or reusable branding.

---

## Audit Conclusion

Static assets should not be deeply audited at this stage.

Portal 2.0 Priority:
Low

Recommendation:
Review folder-by-folder during frontend migration.

Important:
Do not remove assets until all Django template views have been replaced and the Vite frontend is fully operational.