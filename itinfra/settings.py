import os
from dotenv import load_dotenv
from datetime import timedelta
from pathlib import Path
from celery.schedules import crontab
from kombu import Queue, Exchange

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    h.strip().replace("https://", "").replace("http://", "").rstrip("/")
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    'django_celery_results',
    'django_celery_beat',
    'accounts',
    'equipment',
    # 'repairs',
    # 'scrap',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.ForcePasswordChangeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'itinfra.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'itinfra.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.getenv("POSTGRES_DB",       "itinfra"),
        'USER':     os.getenv("POSTGRES_USER",     "postgres"),
        'PASSWORD': os.getenv("POSTGRES_PASSWORD"),
        'HOST':     os.getenv("DB_HOST",           "db"),
        'PORT':     os.getenv("DB_PORT",           "5432"),
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 60,
    }
}

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

# ─────────────────────────────────────────
# INTERNATIONALISATION
# ─────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

# ─────────────────────────────────────────
# STATIC & MEDIA
# ─────────────────────────────────────────

STATIC_URL       = 'static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────
# REST FRAMEWORK
# ─────────────────────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.ActiveUserJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'equipment.pagination.FlexiblePageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ─────────────────────────────────────────
# CORS / CSRF
# ─────────────────────────────────────────

def get_list(value):
    return [item.strip() for item in value.split(',') if item.strip()]

CORS_ALLOWED_ORIGINS   = get_list(os.getenv("CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "False") == "True"
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False") == "True"
CORS_ALLOW_METHODS     = get_list(os.getenv("CORS_ALLOW_METHODS",
    "DELETE,GET,OPTIONS,PATCH,POST,PUT"))
CORS_ALLOW_HEADERS     = get_list(os.getenv("CORS_ALLOW_HEADERS",
    "accept,accept-encoding,authorization,content-type,dnt,origin,user-agent,x-requested-with"))
CSRF_TRUSTED_ORIGINS   = get_list(os.getenv("CSRF_TRUSTED_ORIGINS", ""))

# ─────────────────────────────────────────
# API DOCS
# ─────────────────────────────────────────

SPECTACULAR_SETTINGS = {
    'TITLE':       'IT Infrastructure Management System API',
    'DESCRIPTION': 'API documentation for IT Infrastructure Management System',
    'VERSION':     '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS':    ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [],
}

# ─────────────────────────────────────────
# REDIS — three separate databases
#   DB 0 → Celery broker  (task queue)
#   DB 1 → Celery results (task status)
#   DB 2 → Django cache   (report paths, etc.)
# ─────────────────────────────────────────

REDIS_BROKER_URL = os.getenv("REDIS_BROKER_URL", "redis://127.0.0.1:6379/0")
REDIS_RESULT_URL = os.getenv("REDIS_RESULT_URL", "redis://127.0.0.1:6379/1")
REDIS_CACHE_URL  = os.getenv("REDIS_CACHE_URL",  "redis://127.0.0.1:6379/2")

CACHES = {
    "default": {
        "BACKEND":  "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS":          "django_redis.client.DefaultClient",
            "COMPRESSOR":            "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS":     False,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT":         5,
        },
        "KEY_PREFIX": "itinfra",
        "TIMEOUT":    60 * 30,  # 30 min default TTL
    }
}

# ─────────────────────────────────────────
# CELERY — core settings
# ─────────────────────────────────────────

CELERY_BROKER_URL        = REDIS_BROKER_URL
CELERY_RESULT_BACKEND    = REDIS_RESULT_URL
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_RESULT_EXPIRES    = 60 * 60 * 2   # 2 hours
CELERY_RESULT_COMPRESSION = "zlib"

# ── Default time limits ───────────────────────────────────────────
CELERY_TASK_TIME_LIMIT      = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540

# ── Per-task time limits ──────────────────────────────────────────
CELERY_TASK_ANNOTATIONS = {
    # Full-dataset Excel reports
    'equipment.tasks.task_excel_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_stock_excel_all': {
        'time_limit': 1800, 'soft_time_limit': 1740,
    },
    'equipment.tasks.task_unit_excel_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_region_excel_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_dpu_excel_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_trainingschool_excel_all': {
        'time_limit': 1800, 'soft_time_limit': 1740,
    },

    # Full-dataset PDF reports
    'equipment.tasks.task_pdf_all': {
        'time_limit': 600, 'soft_time_limit': 540,
    },
    'equipment.tasks.task_stock_pdf_all': {
        'time_limit': 600, 'soft_time_limit': 540,
    },
    'equipment.tasks.task_unit_pdf_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_region_pdf_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_dpu_pdf_all': {
        'time_limit': 3600, 'soft_time_limit': 3540,
    },
    'equipment.tasks.task_trainingschool_pdf_all': {
        'time_limit': 1800, 'soft_time_limit': 1740,
    },

    # Per-type Excel reports
    'equipment.tasks.task_excel_by_type': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_stock_excel_by_type': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },

    # Per-type PDF reports
    'equipment.tasks.task_pdf_by_type': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_stock_pdf_by_type': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },

    # Per-location reports
    'equipment.tasks.task_unit_excel_by_unit': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_unit_pdf_by_unit': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_region_excel_by_region': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_region_pdf_by_region': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_dpu_excel_by_dpu': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_dpu_pdf_by_dpu': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_trainingschool_excel_by_school': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
    'equipment.tasks.task_trainingschool_pdf_by_school': {
        'time_limit': 1200, 'soft_time_limit': 1140,
    },
}

# ── Queues ────────────────────────────────────────────────────────
CELERY_TASK_QUEUES = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('reports', Exchange('reports'), routing_key='reports'),
    Queue('prewarm', Exchange('prewarm'), routing_key='prewarm'),
)

CELERY_TASK_DEFAULT_QUEUE       = 'default'
CELERY_TASK_DEFAULT_EXCHANGE    = 'default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'

CELERY_TASK_ROUTES = {
    'equipment.tasks.task_excel_all':                      {'queue': 'reports'},
    'equipment.tasks.task_excel_by_type':                  {'queue': 'reports'},
    'equipment.tasks.task_pdf_all':                        {'queue': 'reports'},
    'equipment.tasks.task_pdf_by_type':                    {'queue': 'reports'},
    'equipment.tasks.task_stock_excel_all':                {'queue': 'reports'},
    'equipment.tasks.task_stock_excel_by_type':            {'queue': 'reports'},
    'equipment.tasks.task_stock_pdf_all':                  {'queue': 'reports'},
    'equipment.tasks.task_stock_pdf_by_type':              {'queue': 'reports'},
    'equipment.tasks.task_unit_excel_all':                 {'queue': 'reports'},
    'equipment.tasks.task_unit_excel_by_unit':             {'queue': 'reports'},
    'equipment.tasks.task_unit_pdf_all':                   {'queue': 'reports'},
    'equipment.tasks.task_unit_pdf_by_unit':               {'queue': 'reports'},
    'equipment.tasks.task_region_excel_all':               {'queue': 'reports'},
    'equipment.tasks.task_region_excel_by_region':         {'queue': 'reports'},
    'equipment.tasks.task_region_pdf_all':                 {'queue': 'reports'},
    'equipment.tasks.task_region_pdf_by_region':           {'queue': 'reports'},
    'equipment.tasks.task_dpu_excel_all':                  {'queue': 'reports'},
    'equipment.tasks.task_dpu_excel_by_dpu':               {'queue': 'reports'},
    'equipment.tasks.task_dpu_pdf_all':                    {'queue': 'reports'},
    'equipment.tasks.task_dpu_pdf_by_dpu':                 {'queue': 'reports'},
    'equipment.tasks.task_trainingschool_excel_all':       {'queue': 'reports'},
    'equipment.tasks.task_trainingschool_excel_by_school': {'queue': 'reports'},
    'equipment.tasks.task_trainingschool_pdf_all':         {'queue': 'reports'},
    'equipment.tasks.task_trainingschool_pdf_by_school':   {'queue': 'reports'},
    'equipment.tasks.prewarm_all_reports':                 {'queue': 'prewarm'},
}

# ── Celery Beat (scheduled tasks) ────────────────────────────────
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE  = {
    "prewarm-all-reports": {
        "task":     "equipment.tasks.prewarm_all_reports",
        "schedule": crontab(minute="*/20"),   # every :00, :20, :40
    },
    "cleanup-old-reports": {
        "task":     "equipment.tasks.cleanup_old_reports",
        "schedule": crontab(hour=3, minute=0),  # daily at 3 AM UTC
    },
}

# ── Worker behaviour ──────────────────────────────────────────────
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# ─────────────────────────────────────────
# REPORT DOWNLOAD TOKEN
# ─────────────────────────────────────────

REPORT_DOWNLOAD_TOKEN_MAX_AGE_SECONDS = int(
    os.getenv("REPORT_DOWNLOAD_TOKEN_MAX_AGE_SECONDS", str(60 * 60 * 24))  # 24 hours
)
REPORT_DOWNLOAD_TOKEN_SALT = os.getenv(
    "REPORT_DOWNLOAD_TOKEN_SALT", "report-download-v1"
)