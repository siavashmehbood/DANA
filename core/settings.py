from pathlib import Path
import os
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/'.env')
DEBUG=os.getenv('DEBUG','True').lower()=='true'
SECRET_KEY=os.getenv('SECRET_KEY','django-insecure-change-this-in-production')
ALLOWED_HOSTS=[x for x in os.getenv('ALLOWED_HOSTS','127.0.0.1,localhost').split(',') if x]
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','accounts','books','shop','reader','gamification','analytics','notifications','support','api','articles']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='core.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='core.wsgi.application'; ASGI_APPLICATION='core.asgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_USER_MODEL='accounts.User'; LOGIN_URL='/login/'; LOGIN_REDIRECT_URL='/'
LANGUAGE_CODE='fa-ir'; TIME_ZONE='Asia/Tehran'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; STATICFILES_DIRS=[BASE_DIR/'static']; MEDIA_URL='/media/'; MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'; FILE_UPLOAD_MAX_MEMORY_SIZE=20*1024*1024
CSRF_COOKIE_SECURE=not DEBUG; SESSION_COOKIE_SECURE=not DEBUG; SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS='SAMEORIGIN'
AUTH_PASSWORD_VALIDATORS=[]
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'; EMAIL_HOST=os.getenv('EMAIL_HOST',''); EMAIL_PORT=int(os.getenv('EMAIL_PORT','587')); EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER',''); EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD',''); EMAIL_USE_TLS=True; DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','noreply@example.com')
