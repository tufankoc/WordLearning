from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q, Max
from datetime import timedelta
import csv
from django.http import HttpResponse
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from .models import Source, Word, WordSourceLink, UserWordKnowledge, UserProfile, Subscription, BillingHistory


# Custom Admin Site for Enhanced Security
class SuperuserAdminSite(AdminSite):
    """Custom admin site that requires superuser access"""
    site_header = "Kelime Vocabulary Admin (Superuser Only)"
    site_title = "Kelime Superuser Admin"
    index_title = "Welcome to Kelime Administration"
    
    def has_permission(self, request):
        """
        Only allow superusers to access this admin site.
        Overrides the default behavior which allows any staff member.
        """
        return request.user.is_active and request.user.is_superuser
    
    def login(self, request, extra_context=None):
        """
        Override login to provide better error messaging for non-superusers
        """
        if request.user.is_authenticated and not request.user.is_superuser:
            raise PermissionDenied("Access denied. Superuser privileges required.")
        return super().login(request, extra_context)


# Create custom admin site instance
superuser_admin_site = SuperuserAdminSite(name='superuser_admin')

# Unregister the default User admin
admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = [
        'is_pro', 'pro_expiry_date', 
        'daily_learning_target', 'daily_new_word_target', 'words_learned_today', 'last_learning_date',
        'filter_stop_words', 'retention_rate', 'known_threshold'
    ]


# Custom Admin Filters
class ActivityFilter(admin.SimpleListFilter):
    title = 'User Activity Level'
    parameter_name = 'activity_level'

    def lookups(self, request, model_admin):
        return (
            ('active_today', 'Active Today'),
            ('active_week', 'Active This Week'),
            ('active_month', 'Active This Month'),
            ('inactive_week', 'Inactive >1 Week'),
            ('inactive_month', 'Inactive >1 Month'),
            ('never_logged_in', 'Never Logged In'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        if self.value() == 'active_today':
            return queryset.filter(
                Q(last_login__date=today) |
                Q(profile__last_learning_date=today)
            ).distinct()
        elif self.value() == 'active_week':
            return queryset.filter(
                Q(last_login__gte=week_ago) |
                Q(profile__last_learning_date__gte=week_ago)
            ).distinct()
        elif self.value() == 'active_month':
            return queryset.filter(
                Q(last_login__gte=month_ago) |
                Q(profile__last_learning_date__gte=month_ago)
            ).distinct()
        elif self.value() == 'inactive_week':
            return queryset.filter(
                Q(last_login__lt=week_ago) | Q(last_login__isnull=True),
                Q(profile__last_learning_date__lt=week_ago) | Q(profile__last_learning_date__isnull=True)
            ).distinct()
        elif self.value() == 'inactive_month':
            return queryset.filter(
                Q(last_login__lt=month_ago) | Q(last_login__isnull=True),
                Q(profile__last_learning_date__lt=month_ago) | Q(profile__last_learning_date__isnull=True)
            ).distinct()
        elif self.value() == 'never_logged_in':
            return queryset.filter(last_login__isnull=True)
        
        return queryset


class WordCountFilter(admin.SimpleListFilter):
    title = 'Word Count Range'
    parameter_name = 'word_count'

    def lookups(self, request, model_admin):
        return (
            ('no_words', 'No Words (0)'),
            ('beginner', 'Beginner (1-10)'),
            ('learning', 'Learning (11-50)'),
            ('intermediate', 'Intermediate (51-100)'),
            ('advanced', 'Advanced (101-500)'),
            ('power_user', 'Power User (500+)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no_words':
            return queryset.annotate(
                word_count=Count('word_knowledge')
            ).filter(word_count=0)
        elif self.value() == 'beginner':
            return queryset.annotate(
                word_count=Count('word_knowledge')
            ).filter(word_count__range=(1, 10))
        elif self.value() == 'learning':
            return queryset.annotate(
                word_count=Count('word_knowledge')
            ).filter(word_count__range=(11, 50))
        elif self.value() == 'intermediate':
            return queryset.annotate(
                word_count=Count('word_knowledge')
            ).filter(word_count__range=(51, 100))
        elif self.value() == 'advanced':
            return queryset.annotate(
                word_count=Count('word_knowledge')
            ).filter(word_count__range=(101, 500))
        elif self.value() == 'power_user':
            return queryset.annotate(
                word_count=Count('word_knowledge')
            ).filter(word_count__gte=500)
        
        return queryset


class SourceCountFilter(admin.SimpleListFilter):
    title = 'Source Count'
    parameter_name = 'source_count'

    def lookups(self, request, model_admin):
        return (
            ('no_sources', 'No Sources'),
            ('few_sources', '1-2 Sources'),
            ('at_limit', 'At Free Limit (3)'),
            ('pro_user', 'Pro User (4+)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no_sources':
            return queryset.annotate(
                source_count=Count('sources')
            ).filter(source_count=0)
        elif self.value() == 'few_sources':
            return queryset.annotate(
                source_count=Count('sources')
            ).filter(source_count__range=(1, 2))
        elif self.value() == 'at_limit':
            return queryset.annotate(
                source_count=Count('sources')
            ).filter(source_count=3, profile__is_pro=False)
        elif self.value() == 'pro_user':
            return queryset.annotate(
                source_count=Count('sources')
            ).filter(source_count__gte=4)
        
        return queryset


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        'username', 'email', 'get_pro_status', 'date_joined', 'last_login',
        'get_total_sources', 'get_known_words', 'get_total_reviews', 
        'get_last_activity', 'get_learning_streak'
    )
    list_filter = (
        'profile__is_pro', 'is_active', 'is_staff', 'date_joined',
        ('last_login', admin.DateFieldListFilter),
        ('profile__last_learning_date', admin.DateFieldListFilter),
        ActivityFilter, WordCountFilter, SourceCountFilter,
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 25
    
    # Add custom fieldsets for user detail view
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Learning Statistics', {
            'fields': (),
            'description': 'Statistics will be displayed in the inline profile section below.'
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related to avoid N+1 queries"""
        return super().get_queryset(request).select_related('profile').prefetch_related(
            'sources', 'word_knowledge', 'subscription', 'billing_history'
        )
    
    def get_pro_status(self, obj):
        try:
            profile = obj.profile
            if profile.is_pro_active():
                color = 'green'
                status = '✓ Pro Active'
                if profile.pro_expiry_date:
                    status += f' (expires {profile.pro_expiry_date.strftime("%Y-%m-%d")})'
            elif profile.is_pro:
                color = 'orange'
                status = '⚠ Pro Expired'
            else:
                color = 'red'
                status = '✗ Free'
            return format_html(
                '<span style="color: {};">{}</span>',
                color, status
            )
        except UserProfile.DoesNotExist:
            return format_html('<span style="color: red;">No Profile</span>')
    get_pro_status.short_description = 'Pro Status'
    
    def get_total_sources(self, obj):
        count = obj.sources.count()
        limit = 3 if not obj.profile.is_pro_active() else "∞"
        color = 'red' if count >= 3 and not obj.profile.is_pro_active() else 'black'
        
        # Add link to view user's sources
        url = reverse('admin:core_source_changelist') + f'?user__id__exact={obj.id}'
        return format_html(
            '<a href="{}" style="color: {};">{}/{}</a>',
            url, color, count, limit
        )
    get_total_sources.short_description = 'Sources'
    
    def get_known_words(self, obj):
        known_count = obj.word_knowledge.filter(state='KNOWN').count()
        total_count = obj.word_knowledge.count()
        
        if total_count > 0:
            percentage = round((known_count / total_count) * 100, 1)
            color = 'green' if percentage > 50 else 'orange' if percentage > 20 else 'red'
        else:
            percentage = 0
            color = 'gray'
        
        # Add link to view user's words
        url = reverse('admin:core_userwordknowledge_changelist') + f'?user__id__exact={obj.id}'
        return format_html(
            '<a href="{}" style="color: {};">{}/{} ({}%)</a>',
            url, color, known_count, total_count, percentage
        )
    get_known_words.short_description = 'Known Words'
    
    def get_total_reviews(self, obj):
        # Count total successful reviews across all words
        total_reviews = obj.word_knowledge.aggregate(
            total=Count('successful_reviews')
        )['total'] or 0
        
        # Get recent reviews (last 7 days)
        recent_reviews = obj.word_knowledge.filter(
            last_review__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        color = 'green' if recent_reviews > 0 else 'gray'
        return format_html(
            '<span style="color: {};">{} total<br/><small>{} recent</small></span>',
            color, total_reviews, recent_reviews
        )
    get_total_reviews.short_description = 'Reviews'
    
    def get_last_activity(self, obj):
        """Get the most recent activity date from various sources"""
        activities = []
        
        # Last login
        if obj.last_login:
            activities.append(obj.last_login)
        
        # Last learning date
        if hasattr(obj, 'profile') and obj.profile.last_learning_date:
            # Convert date to datetime for comparison
            last_learning = timezone.make_aware(
                timezone.datetime.combine(obj.profile.last_learning_date, timezone.datetime.min.time())
            )
            activities.append(last_learning)
        
        # Last word review
        last_review = obj.word_knowledge.filter(
            last_review__isnull=False
        ).aggregate(Max('last_review'))['last_review__max']
        if last_review:
            activities.append(last_review)
        
        # Last source added
        last_source = obj.sources.aggregate(Max('created_at'))['created_at__max']
        if last_source:
            activities.append(last_source)
        
        if activities:
            last_activity = max(activities)
            days_ago = (timezone.now() - last_activity).days
            
            if days_ago == 0:
                color = 'green'
                text = 'Today'
            elif days_ago <= 3:
                color = 'green'
                text = f'{days_ago} days ago'
            elif days_ago <= 7:
                color = 'orange'
                text = f'{days_ago} days ago'
            elif days_ago <= 30:
                color = 'red'
                text = f'{days_ago} days ago'
            else:
                color = 'darkred'
                text = f'{days_ago} days ago'
            
            return format_html(
                '<span style="color: {};" title="{}">{}</span>',
                color, last_activity.strftime('%Y-%m-%d %H:%M'), text
            )
        else:
            return format_html('<span style="color: gray;">Never</span>')
    get_last_activity.short_description = 'Last Activity'
    
    def get_learning_streak(self, obj):
        """Calculate learning streak based on consecutive days with activity"""
        if not hasattr(obj, 'profile'):
            return format_html('<span style="color: gray;">-</span>')
        
        profile = obj.profile
        if not profile.last_learning_date:
            return format_html('<span style="color: gray;">0 days</span>')
        
        # Simple streak calculation based on learning dates
        current_date = timezone.now().date()
        last_learning = profile.last_learning_date
        
        if last_learning == current_date:
            streak = 1  # At least today
            color = 'green'
        elif last_learning == current_date - timedelta(days=1):
            streak = 1  # Yesterday counts as current streak
            color = 'orange'
        else:
            streak = 0
            color = 'gray'
        
        # For a more accurate streak, you'd need to implement streak tracking in models
        return format_html(
            '<span style="color: {};">{} days</span>',
            color, streak
        )
    get_learning_streak.short_description = 'Streak'
    
    actions = ['make_pro', 'make_free', 'extend_pro', 'export_user_stats']
    
    def make_pro(self, request, queryset):
        for user in queryset:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.is_pro = True
            profile.pro_expiry_date = None  # Unlimited
            profile.save()
        self.message_user(request, f"Made {queryset.count()} users Pro (unlimited).")
    make_pro.short_description = "Make selected users Pro (unlimited)"
    
    def make_free(self, request, queryset):
        for user in queryset:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.is_pro = False
            profile.pro_expiry_date = None
            profile.save()
        self.message_user(request, f"Made {queryset.count()} users Free.")
    make_free.short_description = "Make selected users Free"
    
    def extend_pro(self, request, queryset):
        from datetime import timedelta
        expiry_date = timezone.now() + timedelta(days=365)  # 1 year
        for user in queryset:
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.is_pro = True
            profile.pro_expiry_date = expiry_date
            profile.save()
        self.message_user(request, f"Extended Pro for {queryset.count()} users (1 year).")
    extend_pro.short_description = "Extend Pro for 1 year"
    
    def export_user_stats(self, request, queryset):
        """Export detailed user statistics to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_stats.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Email', 'Pro Status', 'Date Joined', 'Last Login',
            'Total Sources', 'Total Words', 'Known Words', 'Learning Words',
            'Total Reviews', 'Recent Reviews (7d)', 'Last Activity',
            'Daily Target', 'Words Today', 'Retention Rate'
        ])
        
        for user in queryset:
            profile = getattr(user, 'profile', None)
            
            # Calculate stats
            total_sources = user.sources.count()
            word_stats = user.word_knowledge.aggregate(
                total=Count('id'),
                known=Count('id', filter=Q(state='KNOWN')),
                learning=Count('id', filter=Q(state='LEARNING')),
                total_reviews=Count('successful_reviews')
            )
            
            recent_reviews = user.word_knowledge.filter(
                last_review__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            # Get last activity
            activities = []
            if user.last_login:
                activities.append(user.last_login)
            if profile and profile.last_learning_date:
                last_learning = timezone.make_aware(
                    timezone.datetime.combine(profile.last_learning_date, timezone.datetime.min.time())
                )
                activities.append(last_learning)
            
            last_activity = max(activities) if activities else None
            
            writer.writerow([
                user.username,
                user.email,
                'Pro' if profile and profile.is_pro_active() else 'Free',
                user.date_joined.strftime('%Y-%m-%d'),
                user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
                total_sources,
                word_stats['total'],
                word_stats['known'],
                word_stats['learning'],
                word_stats['total_reviews'],
                recent_reviews,
                last_activity.strftime('%Y-%m-%d %H:%M') if last_activity else '',
                profile.daily_learning_target if profile else '',
                profile.words_learned_today if profile else '',
                profile.retention_rate if profile else ''
            ])
        
        return response
    export_user_stats.short_description = "Export user statistics to CSV"


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'source_type', 'get_word_count', 'processed', 'created_at')
    list_filter = ('source_type', 'processed', 'created_at', 'user__profile__is_pro')
    search_fields = ('title', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def get_word_count(self, obj):
        count = obj.wordsourcelink_set.count()
        return f"{count} words"
    get_word_count.short_description = 'Words'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('wordsourcelink_set')


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ('text', 'get_frequency', 'get_users_count', 'definition_preview')
    search_fields = ('text', 'definition')
    ordering = ('text',)
    
    def get_frequency(self, obj):
        total_freq = sum(link.frequency for link in obj.wordsourcelink_set.all())
        return f"{total_freq}x"
    get_frequency.short_description = 'Total Frequency'
    
    def get_users_count(self, obj):
        return obj.user_knowledge.count()
    get_users_count.short_description = 'Users Learning'
    
    def definition_preview(self, obj):
        if obj.definition:
            return obj.definition[:100] + "..." if len(obj.definition) > 100 else obj.definition
        return "No definition"
    definition_preview.short_description = 'Definition'


@admin.register(WordSourceLink)
class WordSourceLinkAdmin(admin.ModelAdmin):
    list_display = ('word', 'source', 'frequency', 'source_user', 'source_type')
    list_filter = ('source__source_type', 'source__user__profile__is_pro')
    search_fields = ('word__text', 'source__title', 'source__user__username')
    
    def source_user(self, obj):
        return obj.source.user.username
    source_user.short_description = 'User'
    
    def source_type(self, obj):
        return obj.source.get_source_type_display()
    source_type.short_description = 'Source Type'


@admin.register(UserWordKnowledge)
class UserWordKnowledgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'word', 'state', 'priority', 'successful_reviews', 'difficulty', 'due')
    list_filter = ('state', 'user__profile__is_pro')
    search_fields = ('word__text', 'user__username')
    ordering = ('-due',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'word')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'get_pro_status', 'daily_learning_target', 'daily_new_word_target',
        'get_effective_daily_new_word_target', 'words_learned_today', 'get_total_words', 'last_learning_date'
    )
    list_filter = ('is_pro', 'last_learning_date', 'daily_new_word_target')
    search_fields = ('user__username', 'user__email')
    fields = [
        'user', 'is_pro', 'pro_expiry_date',
        'daily_learning_target', 'daily_new_word_target', 'words_learned_today', 'last_learning_date',
        'filter_stop_words', 'retention_rate', 'known_threshold'
    ]
    readonly_fields = ('user',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('user__word_knowledge')
    
    def get_pro_status(self, obj):
        if obj.is_pro_active():
            color = 'green'
            status = '✓ Pro Active'
            if obj.pro_expiry_date:
                status += f' (expires {obj.pro_expiry_date.strftime("%Y-%m-%d")})'
        elif obj.is_pro:
            color = 'orange'  
            status = '⚠ Pro Expired'
        else:
            color = 'red'
            status = '✗ Free'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, status
        )
    get_pro_status.short_description = 'Pro Status'
    
    def get_effective_daily_new_word_target(self, obj):
        """Show the effective daily new word target."""
        effective = obj.get_effective_daily_new_word_target()
        actual = obj.daily_new_word_target
        
        if obj.can_modify_daily_new_word_target():
            # Pro user - show actual value
            color = 'green'
            text = f"{effective}"
        else:
            # Free user - show fixed value with indication
            color = 'orange'
            if actual != 20:
                text = f"{effective} (locked, set to {actual})"
            else:
                text = f"{effective} (locked)"
        
        return format_html(
            '<span style="color: {};" title="Pro users can customize this value">{}</span>',
            color, text
        )
    get_effective_daily_new_word_target.short_description = 'Effective Daily New Words'
    
    def get_total_words(self, obj):
        total = obj.user.word_knowledge.count()
        known = obj.user.word_knowledge.filter(state='KNOWN').count()
        if total > 0:
            percentage = round((known / total) * 100, 1)
            color = 'green' if percentage > 50 else 'orange'
        else:
            percentage = 0
            color = 'gray'
        
        return format_html(
            '<span style="color: {};">{} total ({} known, {}%)</span>',
            color, total, known, percentage
        )
    get_total_words.short_description = 'Word Progress'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_type', 'status', 'started_at', 'next_billing_date', 'amount')
    list_filter = ('plan_type', 'status', 'started_at')
    search_fields = ('user__username', 'user__email', 'stripe_customer_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'plan_type', 'status')
        }),
        ('Billing Information', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id', 'payment_method', 'amount', 'currency')
        }),
        ('Dates', {
            'fields': ('started_at', 'ends_at', 'next_billing_date', 'cancelled_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'amount', 'currency', 'status', 'invoice_date')
    list_filter = ('status', 'invoice_date', 'currency')
    search_fields = ('user__username', 'user__email', 'invoice_number', 'stripe_invoice_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('user', 'subscription', 'invoice_number', 'amount', 'currency', 'status')
        }),
        ('Payment Information', {
            'fields': ('stripe_invoice_id', 'stripe_payment_intent_id', 'payment_method')
        }),
        ('Details', {
            'fields': ('description', 'line_items')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date', 'paid_at')
        }),
        ('PDF', {
            'fields': ('invoice_pdf_url',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# Customize admin site headers
admin.site.site_header = "Kelime Vocabulary Admin"
admin.site.site_title = "Kelime Admin"
admin.site.index_title = "Welcome to Kelime Administration"

# Also register all models with the superuser admin site
superuser_admin_site.register(User, CustomUserAdmin)
superuser_admin_site.register(Source, SourceAdmin)
superuser_admin_site.register(Word, WordAdmin)
superuser_admin_site.register(WordSourceLink, WordSourceLinkAdmin)
superuser_admin_site.register(UserWordKnowledge, UserWordKnowledgeAdmin)
superuser_admin_site.register(UserProfile, UserProfileAdmin)
superuser_admin_site.register(Subscription, SubscriptionAdmin)
superuser_admin_site.register(BillingHistory, BillingHistoryAdmin)

# Security Enhancement: Override default admin site to require superuser for sensitive models
class SecureUserAdmin(CustomUserAdmin):
    """Enhanced User admin with additional security checks"""
    
    def has_view_permission(self, request, obj=None):
        # Allow superusers full access, staff can only view their own user
        if request.user.is_superuser:
            return True
        if request.user.is_staff and obj and obj == request.user:
            return True
        return False
    
    def has_change_permission(self, request, obj=None):
        # Only superusers can modify user accounts
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete user accounts
        return request.user.is_superuser
    
    def has_add_permission(self, request):
        # Only superusers can create new users through admin
        return request.user.is_superuser

# Re-register User with enhanced security for default admin
admin.site.unregister(User)
admin.site.register(User, SecureUserAdmin)
