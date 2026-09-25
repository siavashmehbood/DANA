import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
class User(AbstractUser):
    username=models.CharField(max_length=150,unique=True,blank=True,null=True)
    phone=models.CharField(max_length=20,unique=True,null=True,blank=True)
    avatar=models.ImageField(upload_to='avatars/',null=True,blank=True)
    wallet_balance=models.DecimalField(max_digits=14,decimal_places=0,default=0,validators=[MinValueValidator(0)])
    xp=models.PositiveIntegerField(default=0); points=models.PositiveIntegerField(default=0)
    purchase_points=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    study_points=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    leaderboard_public=models.BooleanField(default=True)
    referral_code=models.CharField(max_length=12,unique=True,blank=True)
    is_deactivated=models.BooleanField(default=False)
    terms_accepted_at=models.DateTimeField(null=True,blank=True)
    def save(self,*a,**kw):
        if not self.referral_code:self.referral_code=secrets.token_urlsafe(7)[:12].upper()
        if not self.username:self.username=self.phone or f'user_{secrets.token_hex(4)}'
        super().save(*a,**kw)
    @property
    def level(self):
        from gamification.models import GamificationLevel
        level = GamificationLevel.objects.filter(active=True, min_xp__lte=self.xp).order_by('-min_xp').first()
        return level.order if level else 1
class Device(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='devices'); name=models.CharField(max_length=120); token=models.CharField(max_length=255,blank=True); last_seen=models.DateTimeField(default=timezone.now); created_at=models.DateTimeField(auto_now_add=True)
class OTPCode(models.Model):
    phone=models.CharField(max_length=20); code=models.CharField(max_length=128); purpose=models.CharField(max_length=30,default='login'); expires_at=models.DateTimeField(); attempts=models.PositiveSmallIntegerField(default=0); used=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: indexes=[models.Index(fields=['phone','purpose','created_at'])]
class UserSession(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='login_sessions'); session_key=models.CharField(max_length=40,unique=True); device=models.ForeignKey(Device,null=True,blank=True,on_delete=models.SET_NULL); ip=models.GenericIPAddressField(null=True,blank=True); user_agent=models.TextField(blank=True); last_seen=models.DateTimeField(auto_now=True); created_at=models.DateTimeField(auto_now_add=True)
