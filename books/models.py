from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, FileExtensionValidator
from django.utils import timezone
from django.utils.text import slugify
class Author(models.Model): name=models.CharField(max_length=200); bio=models.TextField(blank=True); avatar=models.ImageField(upload_to='authors/',blank=True,null=True)
class Category(models.Model): name=models.CharField(max_length=120); parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE,related_name='children'); slug=models.SlugField(unique=True)
class Level(models.Model): name=models.CharField(max_length=80); order=models.PositiveIntegerField(default=1); min_xp=models.PositiveIntegerField(default=0)
class Book(models.Model):
    VIS=[('public','عمومی'),('private','خصوصی'),('password','رمزدار')]; STATUS=[('draft','پیش‌نویس'),('scheduled','زمان‌بندی‌شده'),('published','منتشر شده')]
    name=models.CharField(max_length=250); slug=models.SlugField(max_length=250,unique=True,blank=True,allow_unicode=True); summary=models.TextField(blank=True); description=models.TextField(blank=True); author=models.ForeignKey(Author,on_delete=models.PROTECT,related_name='books'); category=models.ForeignKey(Category,null=True,blank=True,on_delete=models.SET_NULL); level=models.ForeignKey(Level,null=True,blank=True,on_delete=models.SET_NULL); price=models.DecimalField(max_digits=14,decimal_places=0,default=0,validators=[MinValueValidator(0)]); old_price=models.DecimalField(max_digits=14,decimal_places=0,default=0,validators=[MinValueValidator(0)]); cover=models.ImageField(upload_to='covers/',blank=True,null=True); pdf=models.FileField(upload_to='books/pdf/',blank=True,null=True,validators=[FileExtensionValidator(['pdf'])]); audio=models.FileField(upload_to='books/audio/',blank=True,null=True,validators=[FileExtensionValidator(['mp3','m4a','aac','ogg','wav'])]); visibility=models.CharField(max_length=20,choices=VIS,default='public'); subscription_included=models.BooleanField(default=False, verbose_name='شامل اشتراک'); featured=models.BooleanField(default=False, verbose_name='پیشنهاد ویژه'); access_password=models.CharField(max_length=128,blank=True); status=models.CharField(max_length=20,choices=STATUS,default='draft'); publish_at=models.DateTimeField(null=True,blank=True); preview_percent=models.PositiveSmallIntegerField(default=10,validators=[MaxValueValidator(100)]); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    @property
    def is_published(self): return self.status=='published' or (self.status=='scheduled' and self.publish_at and self.publish_at<=timezone.now())
    def save(self,*args,**kwargs):
        if not self.slug:
            base=slugify(self.name,allow_unicode=True)[:220] or 'book'
            candidate=base; suffix=2
            while Book.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate=f'{base}-{suffix}'[:250]; suffix+=1
            self.slug=candidate
        super().save(*args,**kwargs)
class Chapter(models.Model):
    book=models.ForeignKey(Book,on_delete=models.CASCADE,related_name='chapters'); title=models.CharField(max_length=250); order=models.PositiveIntegerField(); text=models.TextField(blank=True); audio=models.FileField(upload_to='chapters/audio/',blank=True,null=True,validators=[FileExtensionValidator(['mp3','m4a','aac','ogg','wav'])]); duration=models.PositiveIntegerField(default=0)
    class Meta:
        ordering=['order']
        constraints=[models.UniqueConstraint(fields=['book','order'],name='unique_chapter_order_per_book')]
class MediaAsset(models.Model): title=models.CharField(max_length=200); file=models.FileField(upload_to='media/',validators=[FileExtensionValidator(['pdf','mp3','m4a','aac','ogg','wav','jpg','jpeg','png','webp'])]); kind=models.CharField(max_length=30,default='file'); created_at=models.DateTimeField(auto_now_add=True)
