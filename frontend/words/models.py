from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
from datetime import timedelta

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    daily_goal = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class DictionaryWord(models.Model):
    text = models.CharField(max_length=100, unique=True)
    translation = models.CharField(max_length=200)
    frequency = models.IntegerField(default=0)  # Genel kullanım sıklığı
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_words')
    is_verified = models.BooleanField(default=False)  # Doğrulanmış çeviri mi?
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_words')
    verified_at = models.DateTimeField(null=True, blank=True)
    report_count = models.IntegerField(default=0)  # Hatalı çeviri bildirimi sayısı

    def __str__(self):
        return f"{self.text} - {self.translation}"

    class Meta:
        ordering = ['text']
        indexes = [
            models.Index(fields=['text']),
            models.Index(fields=['frequency']),
        ]

class DictionaryReport(models.Model):
    word = models.ForeignKey(DictionaryWord, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'İnceleniyor'),
        ('accepted', 'Kabul Edildi'),
        ('rejected', 'Reddedildi')
    ], default='pending')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='resolved_reports')

    class Meta:
        unique_together = ['word', 'reported_by']  # Bir kullanıcı aynı kelimeyi birden fazla kez raporlayamaz

class Word(models.Model):
    DIFFICULTY_CHOICES = (
        (1, 'Çok Zor'),
        (2, 'Zor'),
        (3, 'Orta'),
        (4, 'Kolay'),
        (5, 'Çok Kolay'),
    )

    STATUS_CHOICES = (
        (0, 'Hiç Çalışılmadı'),
        (1, 'Bilinemedi'),
        (2, 'Az Biliniyor'),
        (3, 'Tam Öğrenildi'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    dictionary_word = models.ForeignKey(DictionaryWord, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_words')
    frequency = models.IntegerField(default=0)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    ease_factor = models.FloatField(default=2.5)
    interval = models.IntegerField(default=1)  # dakika cinsinden
    consecutive_correct = models.IntegerField(default=0)
    review_count = models.IntegerField(default=0)
    last_review = models.DateTimeField(null=True, blank=True)
    next_review = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def translation(self):
        if self.dictionary_word:
            return self.dictionary_word.translation
        return None

    def __str__(self):
        return f"{self.text} ({self.user.username})"

    class Meta:
        unique_together = ['user', 'text']  # Bir kullanıcı aynı kelimeyi birden fazla kez ekleyemez

    def calculate_next_review(self, difficulty):
        """
        Aralıklı tekrar algoritması ile bir sonraki tekrar zamanını hesaplar
        """
        now = timezone.now()
        
        # İlk kez çalışılıyorsa
        if not self.last_review:
            self.last_review = now
            self.next_review = now + timedelta(minutes=5)  # 5 dakika sonra
            self.status = 1
            self.save()
            return

        # Zorluk derecesine göre ease factor ayarla
        if difficulty < 3:  # Zor geldi
            self.ease_factor = max(1.3, self.ease_factor - 0.15)
            self.consecutive_correct = 0
            self.status = 1
        elif difficulty == 3:  # Orta zorlukta
            self.ease_factor = max(1.3, self.ease_factor - 0.05)
            self.consecutive_correct += 1
            self.status = 2
        else:  # Kolay geldi
            self.ease_factor = min(2.5, self.ease_factor + 0.15)
            self.consecutive_correct += 1
            self.status = 3 if self.consecutive_correct >= 2 else 2

        # Interval hesaplama
        if self.consecutive_correct == 0:
            self.interval = 1  # 1 dakika
        elif self.consecutive_correct == 1:
            self.interval = 5  # 5 dakika
        else:
            self.interval = int(self.interval * self.ease_factor)

        # Maksimum interval 30 gün
        self.interval = min(self.interval, 43200)  # 43200 dakika = 30 gün
        
        self.last_review = now
        self.next_review = now + timedelta(minutes=self.interval)
        self.review_count += 1
        self.save()

class ReviewLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    review_date = models.DateTimeField(auto_now_add=True)
    result = models.BooleanField()  # True: Doğru, False: Yanlış
    difficulty = models.IntegerField(choices=Word.DIFFICULTY_CHOICES)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.word.calculate_next_review(self.difficulty)

    class Meta:
        ordering = ['-review_date']

class TextCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']

    def __str__(self):
        return self.name

class TextAnalysis(models.Model):
    TYPE_CHOICES = (
        ('text', 'Text'),
        ('pdf', 'PDF'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    category = models.ForeignKey(TextCategory, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    total_words = models.IntegerField()
    known_words = models.IntegerField()
    comprehension_rate = models.FloatField()
    total_pages = models.IntegerField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    words = models.ManyToManyField(Word)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    class Meta:
        verbose_name = 'Text Analysis'
        verbose_name_plural = 'Text Analyses'
        ordering = ['-created_at']

class CommonWord(models.Model):
    text = models.CharField(max_length=100, unique=True)
    translation = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text} - {self.translation}"

    class Meta:
        ordering = ['text']
