import os
from dotenv import load_dotenv
from datetime import timedelta
from pathlib import Path
import dj_database_url
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")  
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
        'NAME':     os.getenv("POSTGRES_DB",       'itinfra'),
        'USER':     os.getenv("POSTGRES_USER",     'postgres'),
        'PASSWORD': os.getenv("POSTGRES_PASSWORD", ''),
        'HOST':     os.getenv("DB_HOST",           'db'),
        'PORT':     os.getenv("DB_PORT",           '5432'),
    }
}




   

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_USER_MODEL = 'accounts.User'

STORAGES = {
    # Always use the local filesystem — no cloud storage dependency.
    # In Docker, MEDIA_ROOT is backed by a named volume for persistence.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ── No cloud storage — all files saved to local filesystem ────────────────
# Media files persist via the Docker named volume (media_data).
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

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

def get_list(value):
    return [item.strip() for item in value.split(',') if item.strip()]

CORS_ALLOWED_ORIGINS = get_list(os.getenv("CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "False") == "True"
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False") == "True"
CORS_ALLOW_METHODS = get_list(os.getenv("CORS_ALLOW_METHODS", "DELETE,GET,OPTIONS,PATCH,POST,PUT"))
CORS_ALLOW_HEADERS = get_list(os.getenv("CORS_ALLOW_HEADERS", "accept,accept-encoding,authorization,content-type,dnt,origin,user-agent,x-requested-with"))
CSRF_TRUSTED_ORIGINS = get_list(os.getenv("CSRF_TRUSTED_ORIGINS", ""))

SPECTACULAR_SETTINGS = {
    'TITLE': 'IT Infrastructure Management System API',
    'DESCRIPTION': 'API documentation for IT Infrastructure Management System',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [],
}

# Cache + Redis settings
REDIS_BROKER_URL = os.getenv("REDIS_BROKER_URL", "redis://127.0.0.1:6379/0")
REDIS_RESULT_URL = os.getenv("REDIS_RESULT_URL", "redis://127.0.0.1:6379/1")
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://127.0.0.1:6379/2")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "itinfra",
        "TIMEOUT": 60 * 30,
    }
}

# Celery settings
CELERY_BROKER_URL         = REDIS_BROKER_URL
CELERY_RESULT_BACKEND     = REDIS_RESULT_URL
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_RESULT_EXPIRES       = 60 * 30   
CELERY_TASK_TIME_LIMIT      = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540
# Compress large report blobs before storing them in Redis
CELERY_RESULT_COMPRESSION   = "zlib"


CELERY_TASK_QUEUES = {
    "celery":  {"exchange": "celery",  "routing_key": "celery"},
    "prewarm": {"exchange": "prewarm", "routing_key": "prewarm"},
}

CELERY_TASK_ROUTES = {
    "equipment.tasks.prewarm_*": {"queue": "prewarm", "routing_key": "prewarm"},
}

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
  
    "prewarm-all-reports": {
        "task": "equipment.tasks.prewarm_all_reports",
        "schedule": crontab(minute="*/20"),   # :00, :20, :40 of every hour
    },
}


REPORT_DOWNLOAD_TOKEN_MAX_AGE_SECONDS = int(os.getenv("REPORT_DOWNLOAD_TOKEN_MAX_AGE_SECONDS", str(60 * 60 * 24)))  # 24h
REPORT_DOWNLOAD_TOKEN_SALT = os.getenv("REPORT_DOWNLOAD_TOKEN_SALT", "report-download-v1")