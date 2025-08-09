#!/usr/bin/env python
"""
Recalculate word priorities based on stop words filtering settings.
This script updates existing UserWordKnowledge entries to apply content scoring.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kelime.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserWordKnowledge, WordSourceLink, UserProfile
from core.utils import calculate_content_score, is_stop_word
from django.db.models import Sum, Q

def recalculate_user_priorities(user):
    """Recalculate priorities for all words of a specific user."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    filter_stop_words_enabled = profile.get_effective_stop_words_filter()
    
    print(f"\n🔄 Recalculating priorities for user: {user.username}")
    print(f"   Stop words filtering: {'enabled' if filter_stop_words_enabled else 'disabled'}")
    
    # Get all user's word knowledge entries
    user_words = UserWordKnowledge.objects.filter(user=user).select_related('word')
    
    updated_count = 0
    stop_words_updated = 0
    content_words_updated = 0
    
    for knowledge in user_words:
        # Calculate total frequency for this word across all user's sources
        total_frequency = WordSourceLink.objects.filter(
            word=knowledge.word,
            source__user=user
        ).aggregate(total=Sum('frequency'))['total'] or 0
        
        if total_frequency == 0:
            continue
        
        # Calculate new content score
        new_priority = calculate_content_score(
            knowledge.word.text, 
            total_frequency, 
            filter_stop_words_enabled
        )
        
        # Update only if priority changed
        old_priority = knowledge.priority
        if int(new_priority) != old_priority:
            knowledge.priority = int(new_priority)
            knowledge.save()
            updated_count += 1
            
            if is_stop_word(knowledge.word.text):
                stop_words_updated += 1
                print(f"   🚫 {knowledge.word.text:15} - {old_priority:3} → {int(new_priority):3} (stop word)")
            else:
                content_words_updated += 1
                print(f"   ✅ {knowledge.word.text:15} - {old_priority:3} → {int(new_priority):3} (content word)")
    
    print(f"\n📊 Summary for {user.username}:")
    print(f"   Total words updated: {updated_count}")
    print(f"   Stop words updated: {stop_words_updated}")
    print(f"   Content words updated: {content_words_updated}")
    
    return updated_count

def main():
    """Main function to recalculate priorities for all users."""
    print("🎯 Starting Priority Recalculation...")
    print("=" * 50)
    
    # Get all users who have word knowledge entries
    users_with_words = User.objects.filter(
        word_knowledge__isnull=False
    ).distinct()
    
    total_updated = 0
    
    for user in users_with_words:
        updated = recalculate_user_priorities(user)
        total_updated += updated
    
    print("\n" + "=" * 50)
    print(f"🎉 Priority recalculation completed!")
    print(f"   Total users processed: {len(users_with_words)}")
    print(f"   Total words updated: {total_updated}")
    
    # Show top 10 words for testuser after update
    try:
        testuser = User.objects.get(username='testuser')
        print(f"\n📈 Top 10 words for {testuser.username} after update:")
        top_words = UserWordKnowledge.objects.filter(
            user=testuser
        ).select_related('word').order_by('-priority')[:10]
        
        for i, w in enumerate(top_words, 1):
            stop_flag = '🚫' if is_stop_word(w.word.text) else '✅'
            print(f"   {i:2}. {w.word.text:15} - Priority: {w.priority:6} {stop_flag}")
            
    except User.DoesNotExist:
        print("   (testuser not found for demo)")

if __name__ == "__main__":
    main() 