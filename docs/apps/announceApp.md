# announceApp Audit

## Purpose

Handles portal-wide announcements and release/version notes.

---

# models.py

## Keep

### Announcement
- Audience targeting
- Severity levels
- Active/inactive control
- Start/end scheduling
- Priority ordering
- Optional link button
- Dismissible announcement concept

### Version
- Version/release note tracking
- Release date
- Version info
- Slug for stable reference

## Edit Later

### Announcement
- Review whether `message_html` should stay HTML-based or become safer markdown/plain text.
- Convert announcement display to Vite/React.
- Add API endpoint for current announcements.
- Review audience names against Portal 2.0 roles.

### Version
- Consider renaming `Version` to `ReleaseNote` later for clarity.
- Review ordering; current ordering puts older release dates first.

## Pause

- Public announcements can wait unless needed for the public issue/report flow.
- Version/release display can wait until after core portal workflow exists.

## Remove

- Nothing currently.

## Portal 2.0 Notes

This app is reusable but not central to Phase 1.

Recommended use:
- Staff announcements
- Client notices
- Public maintenance/portal notices
- Release notes for portal updates


## Audit Conclusion

announceApp is small, self-contained, and reusable.

No major redesign is currently required.

Future work:
- Add API endpoints for announcements.
- Add API endpoints for release/version history.
- Display announcements and release notes through the Vite frontend.

Priority:
Low