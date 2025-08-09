from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import datetime
import math


class Source(models.Model):
    class SourceType(models.TextChoices):
        URL = 'URL', 'URL'
        TEXT = 'TEXT', 'Text'
        PDF = 'PDF', 'PDF'
        YOUTUBE = 'YOUTUBE', 'YouTube'
        SRT = 'SRT', 'SRT Subtitles'
        EXTENSION = 'EXTENSION', 'Extension'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sources')
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=10, choices=SourceType.choices)
    content = models.TextField()  # For text, URL, or youtube link
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Word(models.Model):
    text = models.CharField(max_length=100, unique=True, db_index=True)
    definition = models.TextField(blank=True, null=True)
    translation_tr = models.TextField(blank=True, null=True)
    # Enrichment fields to facilitate English learning
    part_of_speech = models.CharField(max_length=50, blank=True, null=True)
    phonetic = models.CharField(max_length=100, blank=True, null=True)
    audio_url = models.URLField(blank=True, null=True)
    example_sentence = models.TextField(blank=True, null=True)
    synonyms = models.JSONField(default=list, blank=True)
    antonyms = models.JSONField(default=list, blank=True)
    sources = models.ManyToManyField(Source, through='WordSourceLink')

    def __str__(self):
        return self.text


class WordSourceLink(models.Model):
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    frequency = models.PositiveIntegerField()

    class Meta:
        unique_together = ('word', 'source')


class UserWordKnowledge(models.Model):
    class State(models.TextChoices):
        NEW = 'NEW', 'New'
        LEARNING = 'LEARNING', 'Learning'
        KNOWN = 'KNOWN', 'Known'
        IGNORED = 'IGNORED', 'Ignored'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='word_knowledge')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='user_knowledge')
    state = models.CharField(max_length=10, choices=State.choices, default=State.NEW)
    
    # FSRS Fields
    due = models.DateTimeField(db_index=True)
    stability = models.FloatField(default=0)
    difficulty = models.FloatField(default=5.0)  # Default difficulty for new words
    lapses = models.PositiveIntegerField(default=0)
    last_review = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(default=0, db_index=True)
    
    # New FSRS tracking fields
    review_count = models.PositiveIntegerField(default=0)  # Track successful reviews
    successful_reviews = models.PositiveIntegerField(default=0)  # Count of "I know it" responses

    class Meta:
        unique_together = ('user', 'word')

    def __str__(self):
        return f'{self.user.username} - {self.word.text} ({self.state})'
    
    def calculate_next_review_interval(self, rating, user_retention=0.9):
        """
        Calculate next review interval using simplified FSRS logic.
        
        Args:
            rating: 1 (don't know) or 4 (know it)
            user_retention: Target retention rate (0.9 = 90%)
        
        Returns:
            Number of days until next review
        """
        if rating == 1:  # Don't know
            # Reset for failed review
            self.lapses += 1
            self.stability = max(0.1, self.stability * 0.2)  # Reduce stability significantly
            return 0.1  # Review again in ~2.4 hours
        
        elif rating == 4:  # Know it
            if self.review_count == 0:  # First review
                self.stability = 1.0  # Start with 1 day
            else:
                # FSRS-inspired stability calculation
                factor = 1.3 + (0.1 * (5 - self.difficulty))  # Easier words grow faster
                self.stability *= factor
            
            self.successful_reviews += 1
            
            # Calculate interval based on desired retention
            # interval = stability * ln(retention) / ln(0.9)
            interval = self.stability * (math.log(user_retention) / math.log(0.9))
            return max(1, interval)  # At least 1 day
        
        return 1  # Fallback
    
    def update_difficulty(self, rating):
        """Update difficulty based on user performance."""
        if rating == 1:  # Don't know - increase difficulty
            self.difficulty = min(10.0, self.difficulty + 0.5)
        elif rating == 4:  # Know it - decrease difficulty slightly
            self.difficulty = max(1.0, self.difficulty - 0.1)
    
    def is_ready_for_known_status(self):
        """Check if word meets criteria to be marked as KNOWN."""
        profile = self.user.profile
        return (
            self.successful_reviews >= profile.known_threshold and
            self.state == self.State.LEARNING and
            self.stability >= 7  # Must have at least 7-day stability
        )


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Daily Learning Settings
    daily_learning_target = models.PositiveIntegerField(default=20, help_text="Total daily learning target (legacy)")
    daily_new_word_target = models.PositiveIntegerField(
        default=20, 
        help_text="Number of new words introduced per day (Pro customizable)"
    )
    words_learned_today = models.PositiveIntegerField(default=0)
    last_learning_date = models.DateField(default=datetime.date.today)
    
    # Pro Account Status
    is_pro = models.BooleanField(default=False, help_text="Pro account status")
    pro_expiry_date = models.DateTimeField(null=True, blank=True, help_text="When Pro subscription expires")
    
    # Learning Preferences (Pro Features)
    filter_stop_words = models.BooleanField(
        default=True, 
        help_text="Filter common English words (the, and, is, etc.) from priority ranking (Pro only)"
    )
    
    # FSRS Settings
    retention_rate = models.FloatField(default=0.9, help_text="Target retention rate (0.8-0.95)")
    known_threshold = models.PositiveIntegerField(
        default=5, 
        help_text="Number of successful reviews needed before a word is considered 'known'"
    )

    def __str__(self):
        return f'{self.user.username}\'s Profile'
    
    def check_and_reset_daily_count(self):
        """Resets the daily word count if the date has changed."""
        today = timezone.now().date()
        if self.last_learning_date < today:
            self.words_learned_today = 0
            self.last_learning_date = today
            self.save()
    
    def is_pro_active(self):
        """Check if user has active Pro subscription."""
        if not self.is_pro:
            return False
        
        # If no expiry date set, assume unlimited Pro
        if not self.pro_expiry_date:
            return True
        
        # Check if Pro hasn't expired
        return timezone.now() < self.pro_expiry_date
    
    def can_modify_daily_new_word_target(self):
        """Check if user can modify daily new word target (Pro only)."""
        return self.is_pro_active()
    
    def get_effective_daily_new_word_target(self):
        """Get the effective daily new word target."""
        # Free users always get 20, Pro users can customize
        if not self.is_pro_active():
            return 20
        return self.daily_new_word_target
    
    def can_modify_stop_words_filter(self):
        """Check if user can modify stop words filtering (Pro only)."""
        return self.is_pro_active()
    
    def get_effective_stop_words_filter(self):
        """Get the effective stop words filter setting."""
        # Free users always have filtering enabled
        if not self.is_pro_active():
            return True
        return self.filter_stop_words


class Subscription(models.Model):
    class PlanType(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly Pro Plan'
        YEARLY = 'YEARLY', 'Yearly Pro Plan'
        LIFETIME = 'LIFETIME', 'Lifetime Pro Plan'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'
        PAUSED = 'PAUSED', 'Paused'
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan_type = models.CharField(max_length=10, choices=PlanType.choices, default=PlanType.MONTHLY)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    
    # Billing Information
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, default='Credit Card')
    
    # Dates
    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.get_plan_type_display()} ({self.status})'
    
    def is_active(self):
        """Check if subscription is currently active."""
        if self.status != self.Status.ACTIVE:
            return False
        
        if self.ends_at and timezone.now() > self.ends_at:
            return False
        
        return True
    
    def days_until_renewal(self):
        """Get days until next billing date."""
        if not self.next_billing_date:
            return None
        
        delta = self.next_billing_date.date() - timezone.now().date()
        return max(0, delta.days)


class BillingHistory(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='billing_history')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='billing_history', null=True, blank=True)
    
    # Invoice Information
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    
    # Stripe/Payment Information
    stripe_invoice_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, default='Credit Card')
    
    # Description
    description = models.TextField(blank=True)
    line_items = models.JSONField(default=dict, blank=True)  # Store detailed billing items
    
    # Dates
    invoice_date = models.DateTimeField()
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # PDF Storage
    invoice_pdf_url = models.URLField(blank=True, null=True)  # Stripe hosted invoice URL
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name_plural = 'Billing History'

    def __str__(self):
        return f'Invoice {self.invoice_number} - {self.user.username} - ${self.amount}'
    
    def get_download_url(self):
        """Get URL to download invoice PDF."""
        if self.invoice_pdf_url:
            return self.invoice_pdf_url
        
        # Fallback to generate PDF locally or redirect to Stripe
        return f'/api/invoices/{self.id}/download/'


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()
