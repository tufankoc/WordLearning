from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta, date
import json
from .models import Source, UserWordKnowledge, UserProfile, WordSourceLink, Word, Subscription, BillingHistory
from .forms import CustomUserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from .utils import (
    ENGLISH_STOP_WORDS, is_stop_word, calculate_content_score, 
    get_stop_words_stats
)

# Create your views here.

@login_required
def dashboard(request):
    sources = Source.objects.filter(user=request.user).order_by('-created_at')
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile.check_and_reset_daily_count()

    # Calculate statistics
    total_words = UserWordKnowledge.objects.filter(user=request.user).count()
    known_words = UserWordKnowledge.objects.filter(
        user=request.user,
        state=UserWordKnowledge.State.KNOWN
    ).count()
    
    # Calculate source coverage percentages
    sources_with_coverage = []
    for source in sources:
        word_links = source.wordsourcelink_set.all()
        total_source_words = word_links.count()
        if total_source_words > 0:
            known_words_in_source = UserWordKnowledge.objects.filter(
                user=request.user,
                word__in=[link.word for link in word_links],
                state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
            ).count()
            coverage = (known_words_in_source / total_source_words) * 100
        else:
            coverage = 0
        sources_with_coverage.append({
            'source': source,
            'coverage': round(coverage, 1)
        })

    context = {
        'sources': sources_with_coverage,
        'total_words': total_words,
        'known_words': known_words,
        'sources_count': sources.count(),
        'new_words_today': profile.words_learned_today,
        'daily_target': profile.daily_learning_target,
        'is_pro': profile.is_pro_active(),
        'sources_limit': 3 if not profile.is_pro_active() else None,
        'can_add_source': profile.is_pro_active() or sources.count() < 3,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def source_detail(request, source_id):
    source = get_object_or_404(Source, id=source_id, user=request.user)
    
    # Get sorting and filtering parameters
    sort_by = request.GET.get('sort', 'frequency')  # frequency, word, status
    sort_order = request.GET.get('order', 'desc')  # asc, desc
    filter_status = request.GET.get('status', 'all')  # all, known, unknown, new, learning
    search_query = request.GET.get('search', '').strip()
    
    # Get all word links for this source
    word_links = source.wordsourcelink_set.select_related('word')
    
    # Get user knowledge for all words in this source
    user_knowledge_qs = UserWordKnowledge.objects.filter(
        user=request.user, 
        word__in=[link.word for link in word_links]
    ).select_related('word')
    user_knowledge_dict = {uk.word_id: uk for uk in user_knowledge_qs}
    
    # Build comprehensive word data
    words_data = []
    for link in word_links:
        knowledge_entry = user_knowledge_dict.get(link.word.id)
        
        if knowledge_entry:
            status = knowledge_entry.state
            status_display = knowledge_entry.get_state_display()
            is_known = status in [UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
            knowledge_id = knowledge_entry.id
        else:
            status = 'NEW'
            status_display = 'New'
            is_known = False
            knowledge_id = None
        
        word_data = {
            'text': link.word.text,
            'frequency': link.frequency,
            'status': status,
            'status_display': status_display,
            'is_known': is_known,
            'word_id': link.word.id,
            'knowledge_id': knowledge_id,
            'definition': link.word.definition or '',
            # Enrichment fields for template rendering
            'phonetic': getattr(link.word, 'phonetic', '') or '',
            'audio_url': getattr(link.word, 'audio_url', '') or '',
            'example_sentence': getattr(link.word, 'example_sentence', '') or '',
            'synonyms': getattr(link.word, 'synonyms', []) or [],
        }
        
        # Apply search filter
        if search_query:
            if search_query.lower() not in link.word.text.lower():
                continue
        
        # Apply status filter
        if filter_status != 'all':
            if filter_status == 'known' and not is_known:
                continue
            elif filter_status == 'unknown' and is_known:
                continue
            elif filter_status in ['new', 'learning'] and status.lower() != filter_status:
                continue
        
        words_data.append(word_data)
    
    # Apply sorting
    if sort_by == 'frequency':
        words_data.sort(key=lambda x: x['frequency'], reverse=(sort_order == 'desc'))
    elif sort_by == 'word':
        words_data.sort(key=lambda x: x['text'].lower(), reverse=(sort_order == 'desc'))
    elif sort_by == 'status':
        # Sort by status priority: Known -> Learning -> New
        status_priority = {'KNOWN': 0, 'IGNORED': 0, 'LEARNING': 1, 'NEW': 2}
        words_data.sort(
            key=lambda x: status_priority.get(x['status'], 3), 
            reverse=(sort_order == 'desc')
        )
    
    # Calculate source statistics
    total_words = len(word_links)
    known_words = sum(1 for word in words_data if word['is_known'])
    learning_words = sum(1 for word in words_data if word['status'] == 'LEARNING')
    new_words = sum(1 for word in words_data if word['status'] == 'NEW')
    
    comprehension_percentage = round((known_words / total_words * 100), 1) if total_words > 0 else 0
    
    # Check if there are words from this source to review
    source_words_to_review = UserWordKnowledge.objects.filter(
        user=request.user,
        word__wordsourcelink__source=source,
        state__in=[UserWordKnowledge.State.NEW, UserWordKnowledge.State.LEARNING],
        due__lte=timezone.now()
    ).count()
    
    context = {
        'source': source,
        'words_data': words_data,
        'total_words': total_words,
        'known_words': known_words,
        'learning_words': learning_words,
        'new_words': new_words,
        'comprehension_percentage': comprehension_percentage,
        'source_words_to_review': source_words_to_review,
        
        # Current filters and sorting
        'current_sort': sort_by,
        'current_order': sort_order,
        'current_status': filter_status,
        'current_search': search_query,
        
        # Pagination info
        'filtered_word_count': len(words_data),
    }
    return render(request, 'core/source_detail.html', context)

@login_required
def settings_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Check if user was redirected from admin (for non-staff users)
    show_admin_redirect_message = False
    if request.META.get('HTTP_REFERER') and '/admin/' in request.META.get('HTTP_REFERER'):
        if not request.user.is_staff:
            show_admin_redirect_message = True
    
    if request.method == 'POST':
        # Daily learning target
        target = request.POST.get('daily_target')
        if target and target.isdigit():
            profile.daily_learning_target = int(target)
        
        # Daily new word target (Pro only)
        new_word_target = request.POST.get('daily_new_word_target')
        if new_word_target and new_word_target.isdigit():
            new_target_val = int(new_word_target)
            if profile.can_modify_daily_new_word_target() and 5 <= new_target_val <= 100:
                profile.daily_new_word_target = new_target_val
            elif not profile.can_modify_daily_new_word_target():
                messages.warning(request, "Upgrade to Pro to customize daily new word target.")
        
        # Stop words filtering (Pro only)
        filter_stop_words = request.POST.get('filter_stop_words')
        if profile.can_modify_stop_words_filter():
            # Pro users can toggle this setting
            profile.filter_stop_words = filter_stop_words == 'on'
        elif filter_stop_words is not None and not profile.can_modify_stop_words_filter():
            # Free user tried to change it
            messages.warning(request, "Upgrade to Pro to customize stop words filtering.")
        
        # Known word threshold
        threshold = request.POST.get('known_threshold')
        if threshold and threshold.isdigit():
            threshold_val = int(threshold)
            if 2 <= threshold_val <= 20:  # Reasonable bounds
                profile.known_threshold = threshold_val
        
        # Retention rate
        retention = request.POST.get('retention_rate')
        if retention:
            try:
                retention_val = float(retention)
                if 0.7 <= retention_val <= 0.98:  # Reasonable bounds
                    profile.retention_rate = retention_val
            except ValueError:
                pass
        
        profile.save()
        messages.success(request, "Settings updated successfully!")
        return redirect('settings_page')
    
    context = {
        'current_target': profile.daily_learning_target,
        'current_threshold': profile.known_threshold,
        'current_retention': profile.retention_rate,
        'user_profile': profile,  # Pass the profile object for template access
        'show_admin_redirect_message': show_admin_redirect_message,
    }
    return render(request, 'core/settings.html', context)

@login_required
def statistics_page(request):
    user = request.user
    today = timezone.now().date()
    
    # Get parameters from request
    time_period = request.GET.get('period', '7')
    if time_period not in ['7', '30']:
        time_period = '7'
    
    # Word table parameters
    status_filter = request.GET.get('status', 'all')  # all, known, unknown
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'frequency')  # frequency, word, status
    sort_order = request.GET.get('order', 'desc')  # asc, desc
    page_number = request.GET.get('page', 1)
    
    days_count = int(time_period)
    
    # 1. Daily Learning Summary
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.check_and_reset_daily_count()
    
    # Words reviewed today
    words_reviewed_today = UserWordKnowledge.objects.filter(
        user=user,
        last_review__date=today
    ).select_related('word').order_by('-last_review')
    
    # Learning data for the selected period (7 or 30 days)
    selected_days = [today - timedelta(days=i) for i in range(days_count-1, -1, -1)]
    daily_learning_data = []
    
    for date in selected_days:
        words_on_date = UserWordKnowledge.objects.filter(
            user=user,
            last_review__date=date
        ).count()
        daily_learning_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'words': words_on_date
        })
    
    # 2. Source Comprehension Stats (limit to top 6 for display)
    sources_stats = []
    user_sources = Source.objects.filter(user=user).prefetch_related('wordsourcelink_set__word')[:6]
    
    for source in user_sources:
        word_links = source.wordsourcelink_set.all()
        total_words = word_links.count()
        
        if total_words > 0:
            # Get known words for this source
            word_ids = [link.word_id for link in word_links]
            known_words_count = UserWordKnowledge.objects.filter(
                user=user,
                word_id__in=word_ids,
                state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
            ).count()
            
            comprehension = round((known_words_count / total_words) * 100, 1)
            
            sources_stats.append({
                'source': source,
                'total_words': total_words,
                'known_words': known_words_count,
                'comprehension': comprehension
            })
    
    # Sort by comprehension percentage
    sources_stats.sort(key=lambda x: x['comprehension'], reverse=True)
    
    # 3. Word History Tracker (Recent 20 words - reduced for performance)
    recent_words = UserWordKnowledge.objects.filter(
        user=user,
        last_review__isnull=False
    ).select_related('word').order_by('-last_review')[:20]
    
    # 4. Advanced Stats
    total_words = UserWordKnowledge.objects.filter(user=user).count()
    known_words_count = UserWordKnowledge.objects.filter(
        user=user, 
        state=UserWordKnowledge.State.KNOWN
    ).count()
    learning_words_count = UserWordKnowledge.objects.filter(
        user=user, 
        state=UserWordKnowledge.State.LEARNING
    ).count()
    
    # Top 10 most frequent words learned (both KNOWN and LEARNING states)
    top_frequent_words = UserWordKnowledge.objects.filter(
        user=user,
        state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.LEARNING]
    ).select_related('word').annotate(
        total_frequency=Sum('word__wordsourcelink__frequency',
                           filter=Q(word__wordsourcelink__source__user=user))
    ).order_by('-priority')[:10]
    
    # Get max priority for progress bar scaling
    max_frequency = 0
    if top_frequent_words:
        max_freq_word = top_frequent_words[0]
        max_frequency = max_freq_word.priority or 1
    
    # Calculate review success rate (approximation based on state changes)
    total_reviews = UserWordKnowledge.objects.filter(
        user=user,
        last_review__isnull=False
    ).count()
    
    successful_reviews = UserWordKnowledge.objects.filter(
        user=user,
        state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.LEARNING],
        last_review__isnull=False
    ).count()
    
    success_rate = round((successful_reviews / total_reviews * 100), 1) if total_reviews > 0 else 0
    
    # Calculate learning streak
    streak_days = 0
    current_date = today
    while True:
        daily_reviews = UserWordKnowledge.objects.filter(
            user=user,
            last_review__date=current_date
        ).count()
        
        if daily_reviews > 0:
            streak_days += 1
            current_date -= timedelta(days=1)
        else:
            break
        
        # Prevent infinite loop
        if streak_days > 365:
            break
    
    # 5. FULL WORD FREQUENCY TABLE
    # Get all words with frequency annotation
    words_queryset = UserWordKnowledge.objects.filter(user=user).select_related('word').annotate(
        total_frequency=Sum('word__wordsourcelink__frequency', 
                           filter=Q(word__wordsourcelink__source__user=user))
    )
    
    # Apply search filter
    if search_query:
        words_queryset = words_queryset.filter(word__text__icontains=search_query)
    
    # Apply status filter
    if status_filter == 'known':
        words_queryset = words_queryset.filter(
            state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
        )
    elif status_filter == 'unknown':
        words_queryset = words_queryset.filter(
            state__in=[UserWordKnowledge.State.NEW, UserWordKnowledge.State.LEARNING]
        )
    
    # Apply sorting
    if sort_by == 'frequency':
        order_field = '-priority' if sort_order == 'desc' else 'priority'
    elif sort_by == 'word':
        order_field = '-word__text' if sort_order == 'desc' else 'word__text'
    elif sort_by == 'status':
        # Custom sorting by state priority
        words_queryset = words_queryset.order_by('state' if sort_order == 'asc' else '-state')
        order_field = None
    else:
        order_field = '-priority'  # Default to priority desc
    
    if order_field:
        words_queryset = words_queryset.order_by(order_field)
    
    # Get source information for words in current page to optimize queries
    # We'll get all words first, then limit source queries to displayed words
    all_words_data = list(words_queryset)
    
    # Pagination
    paginator = Paginator(all_words_data, 25)  # 25 words per page
    page_obj = paginator.get_page(page_number)
    
    # Get source information only for words in current page
    word_sources = {}
    current_page_words = page_obj.object_list
    if current_page_words:
        word_ids = [wk.word.id for wk in current_page_words]
        # Optimized query to get sources for current page words only
        sources_query = Source.objects.filter(
            wordsourcelink__word_id__in=word_ids,
            user=user
        ).values('wordsourcelink__word_id', 'title')
        
        for source_data in sources_query:
            word_id = source_data['wordsourcelink__word_id']
            if word_id not in word_sources:
                word_sources[word_id] = []
            if len(word_sources[word_id]) < 3:  # Limit to 3 sources for display
                word_sources[word_id].append(source_data['title'])
    
    # Build word data for template (only for current page)
    words_data = []
    for word_knowledge in current_page_words:
        is_known = word_knowledge.state in [UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
        sources_list = word_sources.get(word_knowledge.word.id, [])
        
        words_data.append({
            'word': word_knowledge.word,
            'knowledge': word_knowledge,
            'total_frequency': word_knowledge.total_frequency or 0,
            'status': word_knowledge.get_state_display(),
            'is_known': is_known,
            'sources': sources_list[:3],  # First 3 sources
            'sources_count': len(sources_list),
            'successful_reviews': word_knowledge.successful_reviews,
            'review_count': word_knowledge.review_count,
        })
    
    context = {
        # Daily Learning
        'words_learned_today': profile.words_learned_today,
        'daily_target': profile.daily_learning_target,
        'words_reviewed_today': words_reviewed_today,
        'daily_learning_data': json.dumps(daily_learning_data),
        'selected_period': time_period,
        
        # Source Stats
        'sources_stats': sources_stats,
        
        # Word History
        'recent_words': recent_words,
        
        # Advanced Stats
        'total_words': total_words,
        'known_words_count': known_words_count,
        'learning_words_count': learning_words_count,
        'top_frequent_words': top_frequent_words,
        'max_frequency': max_frequency,
        'success_rate': success_rate,
        'streak_days': streak_days,
        'total_reviews': total_reviews,
        
        # Word Frequency Table
        'page_obj': page_obj,
        'words_data': words_data,
        'current_status': status_filter,
        'current_search': search_query,
        'current_sort': sort_by,
        'current_order': sort_order,
        'total_filtered_words': len(all_words_data),
    }
    
    return render(request, 'core/statistics.html', context)

@login_required
def help_page(request):
    return render(request, 'core/help.html')

@login_required
def upgrade_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Check if user was redirected from admin (for non-staff users)
    show_admin_redirect_message = False
    if request.META.get('HTTP_REFERER') and '/admin/' in request.META.get('HTTP_REFERER'):
        if not request.user.is_staff:
            show_admin_redirect_message = True
    
    context = {
        'current_sources': Source.objects.filter(user=request.user).count(),
        'is_pro': profile.is_pro_active(),
        'pro_expiry': profile.pro_expiry_date,
        'show_admin_redirect_message': show_admin_redirect_message,
    }
    return render(request, 'core/upgrade.html', context)

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-login the user after successful registration
            login(request, user)
            messages.success(request, f'Welcome to Kelime, {user.username}! Your account has been created successfully.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def review_page(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.check_and_reset_daily_count()
    
    # Count words pending review
    review_words_count = UserWordKnowledge.objects.filter(
        user=request.user,
        due__lte=timezone.now(),
        state=UserWordKnowledge.State.LEARNING
    ).count()
    
    # Count new words available (respecting daily limit)
    new_word_limit = profile.daily_learning_target - profile.words_learned_today
    new_words_count = 0
    if new_word_limit > 0:
        new_words_count = UserWordKnowledge.objects.filter(
            user=request.user,
            due__lte=timezone.now(),
            state=UserWordKnowledge.State.NEW
        ).count()
        new_words_count = min(new_words_count, new_word_limit)
    
    context = {
        'review_words_count': review_words_count,
        'new_words_count': new_words_count,
        'words_learned_today': profile.words_learned_today,
        'daily_target': profile.daily_learning_target,
    }
    return render(request, 'core/review.html', context)

@login_required
def profile_view(request):
    """User profile page with account and subscription details."""
    user = request.user
    profile = user.profile
    
    # Get subscription information
    subscription = None
    try:
        subscription = user.subscription
    except Subscription.DoesNotExist:
        subscription = None
    
    # Get billing history
    billing_history = user.billing_history.filter(status='PAID').order_by('-invoice_date')[:10]
    
    # Calculate account statistics
    total_words = UserWordKnowledge.objects.filter(user=user).count()
    known_words = UserWordKnowledge.objects.filter(user=user, state='KNOWN').count()
    sources_count = Source.objects.filter(user=user).count()
    
    # Gravatar URL
    import hashlib
    email_hash = hashlib.md5(user.email.lower().encode('utf-8')).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?s=128&d=identicon"
    
    context = {
        'user': user,
        'profile': profile,
        'subscription': subscription,
        'billing_history': billing_history,
        'total_words': total_words,
        'known_words': known_words,
        'sources_count': sources_count,
        'gravatar_url': gravatar_url,
        'is_pro': profile.is_pro_active(),
    }
    
    return render(request, 'core/profile.html', context)

# Superuser test function
def is_superuser(user):
    """Test function to check if user is superuser"""
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_dashboard(request):
    """Advanced admin dashboard with detailed user analytics - SUPERUSER ONLY"""
    
    # Double-check superuser status (belt and suspenders approach)
    if not request.user.is_superuser:
        raise PermissionDenied("Access denied. Superuser privileges required.")
    
    # Date range calculations
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # 1. Daily Active Users (last 30 days)
    daily_active_users = []
    for i in range(30):
        date = today - timedelta(days=i)
        # Users who had any activity on this date
        active_count = User.objects.filter(
            Q(last_login__date=date) |
            Q(word_knowledge__last_review__date=date) |
            Q(sources__created_at__date=date) |
            Q(profile__last_learning_date=date)
        ).distinct().count()
        daily_active_users.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': active_count
        })
    daily_active_users.reverse()  # Chronological order
    
    # 2. Sources added per day (last 30 days)
    daily_sources = []
    for i in range(30):
        date = today - timedelta(days=i)
        source_count = Source.objects.filter(created_at__date=date).count()
        daily_sources.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': source_count
        })
    daily_sources.reverse()
    
    # 3. Words learned today
    words_learned_today = UserWordKnowledge.objects.filter(
        last_review__date=today,
        state='KNOWN'
    ).count()
    
    # 4. Top 10 most active users this week
    top_users_week = User.objects.filter(
        Q(last_login__gte=week_ago) |
        Q(word_knowledge__last_review__gte=week_ago) |
        Q(sources__created_at__gte=week_ago)
    ).annotate(
        recent_reviews=Count('word_knowledge__last_review', 
                           filter=Q(word_knowledge__last_review__gte=week_ago)),
        recent_sources=Count('sources', 
                           filter=Q(sources__created_at__gte=week_ago)),
        total_activity=Count('word_knowledge__last_review', 
                           filter=Q(word_knowledge__last_review__gte=week_ago)) +
                      Count('sources', 
                           filter=Q(sources__created_at__gte=week_ago))
    ).order_by('-total_activity')[:10]
    
    # 5. User statistics overview
    total_users = User.objects.count()
    pro_users = User.objects.filter(profile__is_pro=True).count()
    free_users = total_users - pro_users
    
    # Active users (logged in within last 30 days)
    active_users_month = User.objects.filter(last_login__gte=month_ago).count()
    
    # New users this month
    new_users_month = User.objects.filter(date_joined__gte=month_ago).count()
    
    # Churn risk (users who haven't logged in for 30+ days)
    churn_risk_users = User.objects.filter(
        last_login__lt=month_ago,
        last_login__isnull=False
    ).count()
    
    # 6. Learning statistics
    total_words = Word.objects.count()
    total_sources = Source.objects.count()
    total_reviews = UserWordKnowledge.objects.aggregate(
        total=Sum('successful_reviews')
    )['total'] or 0
    
    # Average words per user
    avg_words_per_user = UserWordKnowledge.objects.values('user').annotate(
        word_count=Count('id')
    ).aggregate(avg=Avg('word_count'))['avg'] or 0
    
    # 7. Pro vs Free breakdown with engagement metrics
    user_breakdown = []
    for is_pro in [True, False]:
        label = 'Pro' if is_pro else 'Free'
        users = User.objects.filter(profile__is_pro=is_pro)
        
        breakdown = {
            'label': label,
            'count': users.count(),
            'avg_sources': users.annotate(
                source_count=Count('sources')
            ).aggregate(avg=Avg('source_count'))['avg'] or 0,
            'avg_words': users.annotate(
                word_count=Count('word_knowledge')
            ).aggregate(avg=Avg('word_count'))['avg'] or 0,
            'avg_known_words': users.annotate(
                known_count=Count('word_knowledge', filter=Q(word_knowledge__state='KNOWN'))
            ).aggregate(avg=Avg('known_count'))['avg'] or 0,
        }
        user_breakdown.append(breakdown)
    
    # 8. Recent activity feed
    recent_activities = []
    
    # Recent new users
    recent_users = User.objects.filter(date_joined__gte=week_ago).order_by('-date_joined')[:5]
    for user in recent_users:
        recent_activities.append({
            'type': 'new_user',
            'user': user.username,
            'date': user.date_joined,
            'description': f'New user registered'
        })
    
    # Recent Pro upgrades
    recent_pro_upgrades = User.objects.filter(
        profile__is_pro=True,
        subscription__started_at__gte=week_ago
    ).order_by('-subscription__started_at')[:5]
    for user in recent_pro_upgrades:
        recent_activities.append({
            'type': 'pro_upgrade',
            'user': user.username,
            'date': user.subscription.started_at,
            'description': f'Upgraded to Pro'
        })
    
    # Sort activities by date
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:10]
    
    # 9. System health metrics
    # Users with high word counts (potential power users)
    power_users = User.objects.annotate(
        word_count=Count('word_knowledge')
    ).filter(word_count__gte=100).count()
    
    # Users at source limit (free users with 3+ sources)
    users_at_limit = User.objects.filter(
        profile__is_pro=False
    ).annotate(
        source_count=Count('sources')
    ).filter(source_count__gte=3).count()
    
    context = {
        # Charts data (JSON for JavaScript)
        'daily_active_users_json': json.dumps(daily_active_users),
        'daily_sources_json': json.dumps(daily_sources),
        'user_breakdown_json': json.dumps(user_breakdown),
        
        # Key metrics
        'total_users': total_users,
        'pro_users': pro_users,
        'free_users': free_users,
        'active_users_month': active_users_month,
        'new_users_month': new_users_month,
        'churn_risk_users': churn_risk_users,
        'words_learned_today': words_learned_today,
        
        # Content metrics
        'total_words': total_words,
        'total_sources': total_sources,
        'total_reviews': total_reviews,
        'avg_words_per_user': round(avg_words_per_user, 1),
        
        # Lists
        'top_users_week': top_users_week,
        'recent_activities': recent_activities,
        'user_breakdown': user_breakdown,
        
        # Health metrics
        'power_users': power_users,
        'users_at_limit': users_at_limit,
        
        # Conversion rate (Pro/Total)
        'conversion_rate': round((pro_users / total_users * 100), 1) if total_users > 0 else 0,
    }
    
    return render(request, 'admin/admin_dashboard.html', context)

def landing_page(request):
    """
    Landing page for anonymous users with product introduction.
    Redirects authenticated users to dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Get some stats for the landing page (or use hardcoded values)
    try:
        total_users = User.objects.count()
        total_words_learned = UserWordKnowledge.objects.filter(state='KNOWN').count()
        # Approximate countries (can be hardcoded or calculated from user data)
        countries_count = 22  # Hardcoded for now
    except:
        # Fallback to hardcoded values if database queries fail
        total_users = 1200
        total_words_learned = 85000
        countries_count = 22
    
    context = {
        'total_users': total_users,
        'total_words_learned': total_words_learned,
        'countries_count': countries_count,
    }
    
    return render(request, 'core/landing.html', context)

def enhanced_api_demo(request):
    """Demo page for the Enhanced Source API"""
    return render(request, 'enhanced_source_demo.html')
