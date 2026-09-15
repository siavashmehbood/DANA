from django.db import models
from django.utils import timezone
from accounts.models import User
from books.models import Book
class Coupon(models.Model): code=models.CharField(max_length=50,unique=True); percent=models.PositiveSmallIntegerField(default=0); amount=models.DecimalField(max_digits=14,decimal_places=0,default=0); capacity=models.PositiveIntegerField(default=1); used=models.PositiveIntegerField(default=0); min_order=models.DecimalField(max_digits=14,decimal_places=0,default=0); expires_at=models.DateTimeField(null=True,blank=True); active=models.BooleanField(default=True)
class CartItem(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); book=models.ForeignKey(Book,on_delete=models.CASCADE); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('user','book')
class Order(models.Model): STATUS=[('pending','در انتظار'),('paid','پرداخت شده'),('cancelled','لغو شده'),('gift','هدیه')]; user=models.ForeignKey(User,on_delete=models.PROTECT); subtotal=models.DecimalField(max_digits=14,decimal_places=0); discount=models.DecimalField(max_digits=14,decimal_places=0); tax=models.DecimalField(max_digits=14,decimal_places=0); total=models.DecimalField(max_digits=14,decimal_places=0); status=models.CharField(max_length=20,choices=STATUS,default='pending'); tracking_code=models.CharField(max_length=20,unique=True); gift_to=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL,related_name='received_gifts'); created_at=models.DateTimeField(auto_now_add=True)
class OrderItem(models.Model): order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items'); book=models.ForeignKey(Book,on_delete=models.PROTECT); price=models.DecimalField(max_digits=14,decimal_places=0)
class Entitlement(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='entitlements'); book=models.ForeignKey(Book,on_delete=models.CASCADE); order=models.ForeignKey(Order,null=True,blank=True,on_delete=models.SET_NULL); granted_at=models.DateTimeField(auto_now_add=True); expires_at=models.DateTimeField(null=True,blank=True)
    class Meta: unique_together=('user','book')
class WalletTransaction(models.Model): TYPES=[('credit','شارژ'),('debit','خرید'),('refund','بازگشت'),('reward','جایزه')]; user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='wallet_transactions'); amount=models.DecimalField(max_digits=14,decimal_places=0); type=models.CharField(max_length=20,choices=TYPES); reason=models.CharField(max_length=250); order=models.ForeignKey(Order,null=True,blank=True,on_delete=models.SET_NULL); created_at=models.DateTimeField(auto_now_add=True)
class Referral(models.Model): inviter=models.ForeignKey(User,on_delete=models.CASCADE,related_name='referrals'); invitee=models.OneToOneField(User,on_delete=models.CASCADE,related_name='invited_by'); rewarded=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True)
