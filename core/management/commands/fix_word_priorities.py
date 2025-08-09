"""
Django management command to fix word frequency priorities.

This command recalculates the priority field in UserWordKnowledge entries
to reflect the total frequency of each word across all sources for each user.
This ensures proper frequency-based prioritization in the review queue.

Usage:
    python manage.py fix_word_priorities              # Fix for all users
    python manage.py fix_word_priorities --user-id=1  # Fix for specific user
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum
from core.models import UserWordKnowledge, WordSourceLink


class Command(BaseCommand):
    help = 'Recalculate word priorities based on total frequency across all sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Recalculate priorities for a specific user ID only',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            knowledge_entries = UserWordKnowledge.objects.filter(user_id=user_id)
            self.stdout.write(f'Fixing priorities for user ID: {user_id}')
        else:
            knowledge_entries = UserWordKnowledge.objects.all()
            self.stdout.write('Fixing priorities for all users')

        updated_count = 0
        total_count = knowledge_entries.count()

        for knowledge in knowledge_entries:
            # Calculate total frequency for this word across all user's sources
            total_frequency = WordSourceLink.objects.filter(
                word=knowledge.word,
                source__user=knowledge.user
            ).aggregate(total=Sum('frequency'))['total'] or 0
            
            if knowledge.priority != total_frequency:
                knowledge.priority = total_frequency
                knowledge.save(update_fields=['priority'])
                updated_count += 1
                
                if updated_count % 100 == 0:
                    self.stdout.write(f'Updated {updated_count}/{total_count} entries...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} out of {total_count} word priorities'
            )
        )
        
        if updated_count == 0:
            self.stdout.write(
                self.style.WARNING('No priorities needed updating - all were already correct')
            ) 