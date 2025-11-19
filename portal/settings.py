import os, certifi
from environ import Env

os.environ["SSL_CERT_FILE"] = certifi.where()

env = Env(
    DEBUG=(bool, False)
)
env.read_env()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = env('SECRET_KEY', default='dev-server-only')

DEBUG = env('DEBUG')

# -------- Hosts & CSRF (add your domains) --------
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[
    'localhost', '127.0.0.1',
    'portal.beedev-services.com',
])
CSRF_TRUSTED_ORIGINS = [
    'https://beedev-services.com',
    'https://www.beedev-services.com',
    'https://portal.beedev-services.com',
]


# ---------- Application definition ------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'userApp.apps.UserappConfig',
    'companyApp.apps.CompanyappConfig',
    'ticketApp.apps.TicketappConfig',
    'prospectApp.apps.ProspectappConfig',
    'announceApp.apps.AnnounceappConfig',
    *(['django_browser_reload'] if env.bool('DEBUG', default=False) else []),
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    *( ['django_browser_reload.middleware.BrowserReloadMiddleware'] if env.bool('DEBUG', default=False) else [] ),
]

ROOT_URLCONF = 'portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR,'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'core.context_processors.beedev_defaults',
                'core.context_processors.branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'portal.wsgi.application'

# --------- Database ------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'US/Eastern'
USE_I18N = True
USE_TZ = True

# -------- Auth: shared login + redirects --------
AUTH_USER_MODEL = 'userApp.User'

# -------- Static files: separate source vs. collect dir --------
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------- Production hardening (safe to set; they no-op in dev) --------
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)