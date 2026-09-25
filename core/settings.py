from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/'.env')

def env_bool(name,default=False): return os.getenv(name,str(default)).strip().lower() in {'1','true','yes','on'}
def env_list(name,default=''): return [x.strip() for x in os.getenv(name,default).split(',') if x.strip()]
DEBUG=env_bool('DEBUG',True)
SECRET_KEY=os.getenv('SECRET_KEY','django-insecure-change-this')
ALLOWED_HOSTS=env_list('ALLOWED_HOSTS','127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS=env_list('CSRF_TRUSTED_ORIGINS')
INSTALLED_APPS=['unfold','django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','accounts','books','shop','reader','gamification','analytics','notifications','support','api','articles']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='core.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='core.wsgi.application'; ASGI_APPLICATION='core.asgi.application'
DB_ENGINE=os.getenv('DB_ENGINE','sqlite3')
if DB_ENGINE=='postgresql':
    DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('DB_NAME',''),'USER':os.getenv('DB_USER',''),'PASSWORD':os.getenv('DB_PASSWORD',''),'HOST':os.getenv('DB_HOST','localhost'),'PORT':os.getenv('DB_PORT','5432'),'CONN_MAX_AGE':int(os.getenv('DB_CONN_MAX_AGE','60')),'OPTIONS':{'sslmode':os.getenv('DB_SSLMODE','require')}}}
else: DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_USER_MODEL='accounts.User'; LOGIN_URL='/login/'; LOGIN_REDIRECT_URL='/'
LANGUAGE_CODE='fa-ir'; TIME_ZONE=os.getenv('TIME_ZONE','Asia/Tehran'); USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; STATICFILES_DIRS=[BASE_DIR/'static']; STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':('django.contrib.staticfiles.storage.StaticFilesStorage' if 'test' in __import__('sys').argv else 'whitenoise.storage.CompressedManifestStaticFilesStorage')}}; MEDIA_URL='/media/'; MEDIA_ROOT=BASE_DIR/'media'
def validate_private_media_root(media_root, private_root):
    public_root=Path(media_root).resolve()
    protected_root=Path(private_root).resolve()
    if protected_root == public_root or public_root in protected_root.parents:
        raise RuntimeError('PRIVATE_MEDIA_ROOT must be outside MEDIA_ROOT so protected book files cannot be served by the public media alias.')
    return protected_root
PRIVATE_MEDIA_ROOT=validate_private_media_root(MEDIA_ROOT,os.getenv('PRIVATE_MEDIA_ROOT',str(BASE_DIR/'private_media'))); DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
FILE_UPLOAD_MAX_MEMORY_SIZE=int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE',str(20*1024*1024)))
CSRF_COOKIE_SECURE=env_bool('CSRF_COOKIE_SECURE',not DEBUG); SESSION_COOKIE_SECURE=env_bool('SESSION_COOKIE_SECURE',not DEBUG); SESSION_COOKIE_HTTPONLY=True; SESSION_COOKIE_SAMESITE='Lax'; CSRF_COOKIE_HTTPONLY=env_bool('CSRF_COOKIE_HTTPONLY',False)
SECURE_CONTENT_TYPE_NOSNIFF=True; SECURE_REFERRER_POLICY='same-origin'; X_FRAME_OPTIONS='DENY'; SECURE_SSL_REDIRECT=env_bool('SECURE_SSL_REDIRECT',not DEBUG)
SECURE_HSTS_SECONDS=int(os.getenv('SECURE_HSTS_SECONDS','0' if DEBUG else '31536000')); SECURE_HSTS_INCLUDE_SUBDOMAINS=env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS',not DEBUG); SECURE_HSTS_PRELOAD=env_bool('SECURE_HSTS_PRELOAD',not DEBUG)
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https') if env_bool('TRUST_PROXY_SSL_HEADER',False) else None
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':8}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'; EMAIL_HOST=os.getenv('EMAIL_HOST',''); EMAIL_PORT=int(os.getenv('EMAIL_PORT','587')); EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER',''); EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD',''); EMAIL_USE_TLS=env_bool('EMAIL_USE_TLS',True); DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','noreply@example.com')
ZARINPAL_MERCHANT_ID=os.getenv('ZARINPAL_MERCHANT_ID','')
ZARINPAL_AMOUNT_MULTIPLIER=int(os.getenv('ZARINPAL_AMOUNT_MULTIPLIER','10'))
if not DEBUG and SECRET_KEY=='django-insecure-change-this': raise RuntimeError('SECRET_KEY must be configured when DEBUG=0')
if not DEBUG and not ALLOWED_HOSTS: raise RuntimeError('ALLOWED_HOSTS must be configured when DEBUG=0')
if not DEBUG and any(host in {'*','0.0.0.0'} for host in ALLOWED_HOSTS): raise RuntimeError('ALLOWED_HOSTS must not contain wildcard/public bind hosts when DEBUG=0')
if not DEBUG and not CSRF_TRUSTED_ORIGINS: raise RuntimeError('CSRF_TRUSTED_ORIGINS must be configured with the production HTTPS origin when DEBUG=0')


from django.templatetags.static import static
UNFOLD={'SITE_TITLE':'دانا | مدیریت','SITE_HEADER':'دانا','SITE_SYMBOL':'menu_book','SHOW_HISTORY':True,'SHOW_LANGUAGES':False,'STYLES':[lambda request: static('css/admin-dana.css')],'SIDEBAR':{'show_search':True,'show_all_applications':True}}
