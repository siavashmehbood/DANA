from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
class Author(models.Model): name=models.CharField(max_length=200); bio=models.TextField(blank=True); avatar=models.ImageField(upload_to='authors/',blank=True,null=True)
class Category(models.Model): name=models.CharField(max_length=120); parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE,related_name='children'); slug=models.SlugField(unique=True)
class Level(models.Model): name=models.CharField(max_length=80); order=models.PositiveIntegerField(default=1); min_xp=models.PositiveIntegerField(default=0)
class Book(models.Model):
    VIS=[('public','عمومی'),('private','خصوصی'),('password','رمزدار')]; STATUS=[('draft','پیش‌نویس'),('scheduled','زمان‌بندی‌شده'),('published','منتشر شده')]
    name=models.CharField(max_length=250); slug=models.SlugField(unique=True); summary=models.TextField(blank=True); description=models.TextField(blank=True); author=models.ForeignKey(Author,on_delete=models.PROTECT,related_name='books'); category=models.ForeignKey(Category,null=True,blank=True,on_delete=models.SET_NULL); level=models.ForeignKey(Level,null=True,blank=True,on_delete=models.SET_NULL); price=models.DecimalField(max_digits=14,decimal_places=0,default=0,validators=[MinValueValidator(0)]); old_price=models.DecimalField(max_digits=14,decimal_places=0,default=0,validators=[MinValueValidator(0)]); cover=models.ImageField(upload_to='covers/',blank=True,null=True); pdf=models.FileField(upload_to='books/pdf/',blank=True,null=True); audio=models.FileField(upload_to='books/audio/',blank=True,null=True); visibility=models.CharField(max_length=20,choices=VIS,default='public'); subscription_included=models.BooleanField(default=False, verbose_name='شامل اشتراک'); access_password=models.CharField(max_length=128,blank=True); status=models.CharField(max_length=20,choices=STATUS,default='draft'); publish_at=models.DateTimeField(null=True,blank=True); preview_percent=models.PositiveSmallIntegerField(default=10,validators=[MaxValueValidator(100)]); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    @property
    def is_published(self): return self.status=='published' or (self.status=='scheduled' and self.publish_at and self.publish_at<=timezone.now())
class Chapter(models.Model):
    book=models.ForeignKey(Book,on_delete=models.CASCADE,related_name='chapters'); title=models.CharField(max_length=250); order=models.PositiveIntegerField(); text=models.TextField(blank=True); audio=models.FileField(upload_to='chapters/audio/',blank=True,null=True); duration=models.PositiveIntegerField(default=0)
    class Meta:
        ordering=['order']
        constraints=[models.UniqueConstraint(fields=['book','order'],name='unique_chapter_order_per_book')]
class MediaAsset(models.Model): title=models.CharField(max_length=200); file=models.FileField(upload_to='media/'); kind=models.CharField(max_length=30,default='file'); created_at=models.DateTimeField(auto_now_add=True)
