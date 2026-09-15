from django.db import models
from accounts.models import User
from books.models import Book, Chapter
from articles.models import Article


class ReadingProgress(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); book=models.ForeignKey(Book,on_delete=models.CASCADE); progress=models.DecimalField(max_digits=5,decimal_places=2,default=0); current_page=models.PositiveIntegerField(default=0); current_chapter=models.ForeignKey(Chapter,null=True,blank=True,on_delete=models.SET_NULL); seconds=models.PositiveIntegerField(default=0); audio_seconds=models.PositiveIntegerField(default=0); updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('user','book')
class Bookmark(models.Model): user=models.ForeignKey(User,on_delete=models.CASCADE); book=models.ForeignKey(Book,on_delete=models.CASCADE); page=models.PositiveIntegerField(); title=models.CharField(max_length=150,blank=True); created_at=models.DateTimeField(auto_now_add=True)
class Note(models.Model): user=models.ForeignKey(User,on_delete=models.CASCADE); book=models.ForeignKey(Book,on_delete=models.CASCADE); page=models.PositiveIntegerField(); text=models.TextField(); created_at=models.DateTimeField(auto_now_add=True)
class ProblemReport(models.Model): user=models.ForeignKey(User,on_delete=models.CASCADE); book=models.ForeignKey(Book,on_delete=models.CASCADE); text=models.TextField(); status=models.CharField(max_length=20,default='open'); created_at=models.DateTimeField(auto_now_add=True)
class Review(models.Model): user=models.ForeignKey(User,on_delete=models.CASCADE); book=models.ForeignKey(Book,on_delete=models.CASCADE); rating=models.PositiveSmallIntegerField(default=5); text=models.TextField(); admin_score=models.PositiveSmallIntegerField(null=True,blank=True); admin_reply=models.TextField(blank=True); approved=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True)


class SavedWord(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='saved_words')
    word=models.CharField(max_length=180)
    normalized_word=models.CharField(max_length=180)
    source_language=models.CharField(max_length=10,default='en')
    article=models.ForeignKey(Article,null=True,blank=True,on_delete=models.SET_NULL,related_name='saved_words')
    meaning_fa=models.CharField(max_length=500,blank=True)
    pronunciation_fa=models.CharField(max_length=300,blank=True)
    example_en=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    last_reviewed=models.DateTimeField(null=True,blank=True)
    review_count=models.PositiveIntegerField(default=0)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','normalized_word'],name='unique_saved_word_per_user')]
        ordering=['-created_at']

    def __str__(self):
        return self.word
