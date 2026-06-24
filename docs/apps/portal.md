# portal

## Purpose

Project-level Django configuration.

---

# settings.py

## Keep

### Environment Configuration
- django-environ usage
- Environment variables
- Secret key management
- Database configuration

### Security
- CSRF configuration
- Secure cookies
- SSL redirect support
- Trusted origins

### Authentication
- Custom User model
- Login/logout configuration

### Static/Media
- Static file configuration
- Media file configuration
- WhiteNoise support

### Database
- MySQL configuration

### REST Framework
- DRF installation

---

## Edit Later

### Installed Apps

Review after Portal 2.0 rebuild:

Current apps:

- userApp
- companyApp
- ticketApp
- prospectApp
- announceApp
- onboardingApp
- core

Additional apps may be added:

- projectApp
- apiApp
- notificationApp

### Email Configuration

Current:

- Console backend

Future:

- Production email backend
- BeeDev mail service
- Notification emails

### Templates

Current configuration is Django-template based.

Once Vite becomes primary frontend:

- Django templates become minimal.
- React/Vite becomes primary UI.

---

## Pause

None.

---

## Remove

None.

---

## Portal 2.0 Notes

settings.py is infrastructure.

Most of this file should survive the Portal 2.0 rebuild with only minor adjustments.