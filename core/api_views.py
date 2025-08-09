from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from django.conf import settings
from .models import Source, Word, WordSourceLink, UserWordKnowledge, UserProfile
from .serializers import SourceSerializer, UserWordKnowledgeSerializer, EnhancedSourceSerializer
from .utils import (
    extract_words_from_text, fetch_word_definition, ENGLISH_STOP_WORDS, is_stop_word, calculate_content_score, 
    get_stop_words_stats, get_content_preview
)
from .content_parsers import (
    CONTENT_PARSERS, 
    ContentParsingError, 
    SecurityError
)
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
import datetime
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from datetime import timedelta
import re
from collections import Counter
import logging

logger = logging.getLogger(__name__)

def _get_next_word(user, exclude_pk=None):
    """
    Fetches the next word in the user's review queue, excluding a specific word if provided.
    Uses daily_new_word_target to limit new words shown per day.
    """
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.check_and_reset_daily_count()

    # Base querysets ordering by priority (content scoring) instead of raw frequency
    review_words_qs = UserWordKnowledge.objects.filter(
        user=user, 
        due__lte=timezone.now(), 
        state=UserWordKnowledge.State.LEARNING
    ).order_by('-priority', 'due')
    
    new_words_qs = UserWordKnowledge.objects.filter(
        user=user, 
        due__lte=timezone.now(), 
        state=UserWordKnowledge.State.NEW
    ).order_by('-priority', 'due')

    if exclude_pk:
        if isinstance(exclude_pk, (list, tuple)):
            review_words_qs = review_words_qs.exclude(pk__in=exclude_pk)
            new_words_qs = new_words_qs.exclude(pk__in=exclude_pk)
        else:
            review_words_qs = review_words_qs.exclude(pk=exclude_pk)
            new_words_qs = new_words_qs.exclude(pk=exclude_pk)

    # Apply daily limit for NEW words using daily_new_word_target
    effective_target = profile.get_effective_daily_new_word_target()
    new_word_limit = effective_target - profile.words_learned_today
    
    new_words = []
    if new_word_limit > 0:
        new_words = list(new_words_qs[:new_word_limit])

    # Combine review and new words, prioritizing by content scoring
    # Review words are NOT limited by daily_new_word_target
    all_words = list(review_words_qs) + new_words
    
    # Sort by priority (content scoring) then by due date
    all_words.sort(key=lambda x: (-x.priority, x.due))
    
    return all_words[0] if all_words else None

class NextWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        next_word = _get_next_word(request.user)
        if next_word:
            serializer = UserWordKnowledgeSerializer(next_word)
            return Response(serializer.data)
        return Response({"message": "No words to review right now."}, status=status.HTTP_204_NO_CONTENT)

class EnhancedSourceCreateAPIView(generics.CreateAPIView):
    """Enhanced source creation with multiple input type support."""
    serializer_class = EnhancedSourceSerializer
    permission_classes = [IsAuthenticated]

    def _determine_source_type_and_extract_content(self, validated_data):
        """
        Determine source type and extract content from various input types.
        
        Returns:
            Tuple of (source_type, content, metadata)
        """
        logger.info("=== CONTENT EXTRACTION START ===")
        
        # Log what input types are present
        input_types_present = []
        for field in ['pdf_file', 'srt_file', 'web_url', 'youtube_url', 'manual_text']:
            if field in validated_data and validated_data[field]:
                input_types_present.append(field)
        
        logger.info(f"Input types detected: {input_types_present}")
        logger.info(f"Validated data keys: {list(validated_data.keys())}")
        
        if len(input_types_present) == 0:
            logger.error("No input types found in validated_data")
            raise ContentParsingError("No valid input provided")
        
        if len(input_types_present) > 1:
            logger.error(f"Multiple input types found: {input_types_present}")
            raise ContentParsingError("Multiple input types provided. Please provide only one.")
        
        content = ""
        metadata = {}
        source_type = None
        
        try:
            # Handle PDF files
            if 'pdf_file' in validated_data and validated_data['pdf_file']:
                logger.info("Processing PDF file...")
                source_type = Source.SourceType.PDF
                pdf_file = validated_data['pdf_file']
                
                logger.info(f"PDF file info: name={pdf_file.name}, size={pdf_file.size}")
                
                # Read file content
                file_content = pdf_file.read()
                logger.info(f"Read {len(file_content)} bytes from PDF")
                
                # Reset file pointer for potential re-reads
                pdf_file.seek(0)
                
                # Parse content
                content, metadata = CONTENT_PARSERS['pdf'](file_content)
                logger.info(f"PDF parsing successful: {len(content)} characters extracted")
                
            # Handle SRT files
            elif 'srt_file' in validated_data and validated_data['srt_file']:
                logger.info("Processing SRT file...")
                source_type = Source.SourceType.SRT  # Use proper enum value
                srt_file = validated_data['srt_file']
                
                logger.info(f"SRT file info: name={srt_file.name}, size={srt_file.size}")
                
                # Read file content
                file_content = srt_file.read()
                logger.info(f"Read {len(file_content)} bytes from SRT")
                
                # Reset file pointer
                srt_file.seek(0)
                
                # Parse content
                content, metadata = CONTENT_PARSERS['srt'](file_content)
                logger.info(f"SRT parsing successful: {len(content)} characters extracted")
                
            # Handle web URLs
            elif 'web_url' in validated_data and validated_data['web_url']:
                logger.info("Processing web URL...")
                source_type = Source.SourceType.URL
                web_url = validated_data['web_url'].strip()
                
                logger.info(f"Web URL: {web_url}")
                
                # Parse content
                content, metadata = CONTENT_PARSERS['web'](web_url)
                logger.info(f"Web scraping successful: {len(content)} characters extracted")
                
            # Handle YouTube URLs
            elif 'youtube_url' in validated_data and validated_data['youtube_url']:
                logger.info("Processing YouTube URL...")
                source_type = Source.SourceType.YOUTUBE
                youtube_url = validated_data['youtube_url'].strip()
                
                logger.info(f"YouTube URL: {youtube_url}")
                
                # Parse content
                content, metadata = CONTENT_PARSERS['youtube'](youtube_url)
                logger.info(f"YouTube transcript extraction successful: {len(content)} characters extracted")
                
            # Handle manual text
            elif 'manual_text' in validated_data and validated_data['manual_text']:
                logger.info("Processing manual text...")
                source_type = Source.SourceType.TEXT
                content = validated_data['manual_text'].strip()
                
                logger.info(f"Manual text: {len(content)} characters")
                
                metadata = {
                    'characters': len(content),
                    'words': len(content.split()) if content else 0,
                    'source': 'manual_input'
                }
                
            else:
                logger.error("No valid input found in validated_data")
                logger.error(f"Available keys: {list(validated_data.keys())}")
                raise ContentParsingError("No valid input provided")
        
        except (ContentParsingError, SecurityError) as e:
            logger.error(f"Content parsing error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected parsing error: {str(e)}", exc_info=True)
            raise ContentParsingError(f"Unexpected error during content parsing: {str(e)}")
        
        # Validate extracted content
        if not content or not content.strip():
            logger.error("No content extracted from source")
            raise ContentParsingError("No readable content could be extracted from the provided source")
        
        logger.info(f"Content extraction successful:")
        logger.info(f"  - Source type: {source_type}")
        logger.info(f"  - Content length: {len(content)} characters")
        logger.info(f"  - Metadata: {metadata}")
        logger.info("=== CONTENT EXTRACTION END ===")
        
        return source_type, content, metadata

    def perform_create(self, serializer):
        """Override perform_create to handle enhanced content processing."""
        user = self.request.user
        
        logger.info(f"=== SOURCE CREATION START ===")
        logger.info(f"User: {user.id} ({user.username})")
        logger.info(f"Request method: {self.request.method}")
        logger.info(f"Content-Type: {self.request.content_type}")
        
        # Log request data safely
        if hasattr(self.request, 'data') and self.request.data:
            safe_data = {}
            for key, value in self.request.data.items():
                if hasattr(value, 'read'):  # File object
                    safe_data[key] = f"<File: {getattr(value, 'name', 'unknown')} - {getattr(value, 'size', 'unknown')} bytes>"
                else:
                    safe_data[key] = str(value)[:100]  # Truncate long text
            logger.info(f"Request data: {safe_data}")
        
        # Check Pro account limits for free users
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        if not profile.is_pro_active():
            source_count = Source.objects.filter(user=user).count()
            logger.info(f"Free user {user.username} has {source_count} sources")
            if source_count >= 3:
                logger.warning(f"User {user.username} exceeded free source limit")
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Free accounts are limited to 3 sources. Upgrade to Pro for unlimited sources.")
        
        try:
            # Extract content from input
            validated_data = serializer.validated_data
            logger.info(f"Serializer validated data keys: {list(validated_data.keys())}")
            
            source_type, content, parsing_metadata = self._determine_source_type_and_extract_content(validated_data)
            
            # Create the source with extracted content
            logger.info(f"Creating source with type: {source_type}")
            source = serializer.save(
                user=user,
                source_type=source_type,
                content=content
            )
            
            logger.info(f"Source created with ID: {source.id}")
            
            # Store parsing metadata for response
            serializer.instance.parsing_metadata = parsing_metadata
            
            # Process words
            words_processed = self._process_source_words(source, user)
            logger.info(f"Processed {words_processed} unique words")
            
        except (ContentParsingError, SecurityError) as e:
            logger.error(f"Content parsing error for user {user.id}: {str(e)}")
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f"Content parsing failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in source creation for user {user.id}: {str(e)}", exc_info=True)
            from rest_framework.exceptions import APIException
            raise APIException("An unexpected error occurred while processing your content.")

    def _process_source_words(self, source, user):
        """Process and tokenize words from source content with stop words filtering."""
        logger.info(f"=== WORD PROCESSING START for source {source.id} ===")
        
        # Get user's stop words filtering preference
        profile, _ = UserProfile.objects.get_or_create(user=user)
        filter_stop_words_enabled = profile.get_effective_stop_words_filter()
        
        # 1. Tokenize the content
        content_lower = source.content.lower()
        word_list = re.findall(r'\b[a-zA-Z]+\b', content_lower)
        word_counts = Counter(word_list)
        
        # Get stop words statistics
        stop_words_stats = get_stop_words_stats(word_counts)
        
        logger.info(f"Tokenization results:")
        logger.info(f"  - Total words: {len(word_list)}")
        logger.info(f"  - Unique words: {len(word_counts)}")
        logger.info(f"  - Stop words: {stop_words_stats['stop_words']['unique_count']} unique ({stop_words_stats['stop_words']['percentage_of_unique']:.1f}%)")
        logger.info(f"  - Content words: {stop_words_stats['content_words']['unique_count']} unique ({stop_words_stats['content_words']['percentage_of_unique']:.1f}%)")
        logger.info(f"  - Stop words filtering: {'enabled' if filter_stop_words_enabled else 'disabled'}")
        logger.info(f"  - Top 10 frequent: {dict(word_counts.most_common(10))}")
        
        if not word_counts:
            logger.warning("No words found in content")
            source.processed = True
            source.save()
            return 0
        
        # 2. Process each word with content scoring
        words_to_process = []
        words_created = 0
        stop_words_processed = 0
        content_words_processed = 0
        
        for word_text, frequency in word_counts.items():
            # Calculate content score (applies stop word penalty if enabled)
            content_score = calculate_content_score(word_text, frequency, filter_stop_words_enabled)
            
            # Track stop words vs content words
            if is_stop_word(word_text):
                stop_words_processed += 1
            else:
                content_words_processed += 1
            
            # Create or get the Word object
            word, created = Word.objects.get_or_create(text=word_text)
            if created:
                words_created += 1
                logger.debug(f"Created new word: {word_text} ({'stop word' if is_stop_word(word_text) else 'content word'})")
            
            # Fetch definition for new words (in background if possible)
            if created:
                try:
                    if getattr(settings, 'FETCH_DEFINITIONS_SYNC', False):
                        from .utils import enrich_word_with_dictionaryapi
                        enriched = enrich_word_with_dictionaryapi(word_text)
                        if enriched.get('definition') and not word.definition:
                            word.definition = enriched['definition']
                        # fill enrichment fields if available
                        for field in ['phonetic', 'audio_url', 'example_sentence', 'part_of_speech']:
                            if enriched.get(field):
                                setattr(word, field, enriched[field])
                        if enriched.get('synonyms'):
                            word.synonyms = enriched['synonyms']
                        if enriched.get('antonyms'):
                            word.antonyms = enriched['antonyms']
                    if not word.definition:
                        word.definition = f"Definition for {word_text} (placeholder)"
                    word.save()
                    logger.debug(f"Enriched word: {word_text}")
                except Exception as e:
                    logger.warning(f"Failed to enrich {word_text}: {e}")
            
            words_to_process.append((word, frequency, content_score))
        
        logger.info(f"Created {words_created} new word objects")
        logger.info(f"Processing {stop_words_processed} stop words, {content_words_processed} content words")
        
        # 3. Create WordSourceLink entries and UserWordKnowledge
        word_links_to_create = []
        knowledge_created = 0
        knowledge_updated = 0
        
        for word, frequency, content_score in words_to_process:
            # Create the link between word, source, and user with frequency
            word_links_to_create.append(
                WordSourceLink(
                    word=word, 
                    source=source, 
                    frequency=frequency
                )
            )
            
            # Create or update UserWordKnowledge with content score as priority
            knowledge, created = UserWordKnowledge.objects.get_or_create(
                user=user,
                word=word,
                defaults={
                    'state': UserWordKnowledge.State.NEW,
                    'due': timezone.now(),
                    'priority': int(content_score),  # Use content score instead of raw frequency
                }
            )
            
            if created:
                knowledge_created += 1
            else:
                # Update priority with accumulated content score
                existing_total = WordSourceLink.objects.filter(
                    word=word,
                    source__user=user
                ).aggregate(total=Sum('frequency'))['total'] or 0
                
                # Calculate new content score for accumulated frequency
                new_total_frequency = existing_total + frequency
                new_content_score = calculate_content_score(word.text, new_total_frequency, filter_stop_words_enabled)
                
                knowledge.priority = int(new_content_score)
                knowledge.save()
                knowledge_updated += 1
        
        # Bulk create the word-source links
        if word_links_to_create:
            WordSourceLink.objects.bulk_create(word_links_to_create)
            logger.info(f"Created {len(word_links_to_create)} word-source links")
        
        logger.info(f"Knowledge entries: {knowledge_created} created, {knowledge_updated} updated")
        logger.info(f"Stop words filtering applied: {filter_stop_words_enabled}")
        
        # Mark source as processed
        source.processed = True
        source.save()
        
        logger.info(f"=== WORD PROCESSING END ===")
        return len(word_counts)

    def create(self, request, *args, **kwargs):
        """Override create to provide enhanced analysis data in response."""
        logger.info(f"=== API REQUEST START ===")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create the source and process words
            self.perform_create(serializer)
            source = serializer.instance
            parsing_metadata = getattr(source, 'parsing_metadata', {})
            
            # Generate analysis data for response
            content_lower = source.content.lower()
            word_list = re.findall(r'\b[a-zA-Z]+\b', content_lower)
            word_counts = Counter(word_list)
            
            total_words = sum(word_counts.values())
            unique_words = len(word_counts)
            
            if unique_words == 0:
                analysis = {
                    'coverage': 100,
                    'total_words': 0,
                    'unique_words': 0,
                    'known_words': 0,
                    'new_words': 0,
                    'processing_status': 'no_words_found'
                }
            else:
                # Get user's known words for analysis
                user_known_words = set(UserWordKnowledge.objects.filter(
                    user=request.user,
                    state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
                ).values_list('word__text', flat=True))
                
                # Count words by status
                known_words_in_source = user_known_words.intersection(word_counts.keys())
                known_word_count = len(known_words_in_source)
                new_word_count = unique_words - known_word_count
                coverage = (known_word_count / unique_words * 100) if unique_words > 0 else 0
                
                analysis = {
                    'coverage': round(coverage, 2),
                    'total_words': total_words,
                    'unique_words': unique_words,
                    'known_words': known_word_count,
                    'new_words': new_word_count,
                    'words_processed': unique_words,
                    'processing_status': 'success'
                }
            
            # Add parsing metadata to analysis
            analysis.update(parsing_metadata)
            
            # Generate content preview
            content_preview = get_content_preview(source.content)
            
            # Enhanced response format matching the requested example
            headers = self.get_success_headers(serializer.data)
            response_data = {
                'status': 'success',
                'source_id': source.id,
                'words_extracted': unique_words,
                'id': source.id,
                'title': source.title,
                'source_type': source.source_type,
                'created_at': source.created_at.isoformat(),
                'analysis': analysis,
                'content_preview': content_preview,
                'success_message': f"✅ {unique_words} unique words extracted and processed successfully!",
                'debug_info': {
                    'parsing_metadata': parsing_metadata,
                    'request_user': request.user.username,
                    'processed_at': timezone.now().isoformat()
                }
            }
            
            logger.info(f"=== API REQUEST SUCCESS ===")
            logger.info(f"Response summary: {unique_words} words from source {source.id}")
            
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"=== API REQUEST FAILED ===")
            logger.error(f"Error: {str(e)}", exc_info=True)
            raise

class SourceListCreateAPIView(generics.ListCreateAPIView):
    """Legacy API view for backward compatibility."""
    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Source.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        """Override perform_create to handle tokenization and word processing."""
        # Check Pro account limits for free users
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        if not profile.is_pro_active():
            source_count = Source.objects.filter(user=user).count()
            if source_count >= 3:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Free accounts are limited to 3 sources. Upgrade to Pro for unlimited sources.")
        
        # Save the source with the authenticated user
        source = serializer.save(user=self.request.user)
        
        # 1. Automatically tokenize the content field
        content_lower = source.content.lower()
        word_list = re.findall(r'\b[a-zA-Z]+\b', content_lower)
        word_counts = Counter(word_list)
        
        if not word_counts:
            # No words found, mark as processed and return
            source.processed = True
            source.save()
            return
        
        # 2. For each word: Create or retrieve Word object (include ALL words, even known ones)
        words_to_process = []
        for word_text, frequency in word_counts.items():
            # Create or get the Word object
            word, created = Word.objects.get_or_create(text=word_text)
            
            # Fetch definition for new words
            if created:
                if getattr(settings, 'FETCH_DEFINITIONS_SYNC', False):
                    from .utils import enrich_word_with_dictionaryapi
                    enriched = enrich_word_with_dictionaryapi(word_text)
                    updated = False
                    if enriched.get('definition') and not word.definition:
                        word.definition = enriched['definition']
                        updated = True
                    for field in ['phonetic', 'audio_url', 'example_sentence', 'part_of_speech']:
                        if enriched.get(field):
                            setattr(word, field, enriched[field])
                            updated = True
                    if enriched.get('synonyms'):
                        word.synonyms = enriched['synonyms']
                        updated = True
                    if enriched.get('antonyms'):
                        word.antonyms = enriched['antonyms']
                        updated = True
                    if updated:
                        word.save()
            
            words_to_process.append((word, frequency))
        
        # 3. Create WordSourceLink (WordInstance equivalent) for each word
        word_links_to_create = []
        knowledge_to_create = []
        
        for word, frequency in words_to_process:
            # Create the link between word, source, and user with frequency
            word_links_to_create.append(
                WordSourceLink(
                    word=word, 
                    source=source, 
                    frequency=frequency
                )
            )
            
            # Create UserWordKnowledge if it doesn't exist
            knowledge, created = UserWordKnowledge.objects.get_or_create(
                user=self.request.user,
                word=word,
                defaults={
                    'state': UserWordKnowledge.State.NEW,
                    'due': timezone.now(),
                    'priority': frequency,
                }
            )
            
            # Update priority if knowledge already existed
            if not created:
                # Calculate total frequency across all sources for this user and word
                total_frequency = WordSourceLink.objects.filter(
                    word=word,
                    source__user=self.request.user
                ).aggregate(total=Sum('frequency'))['total'] or 0
                knowledge.priority = total_frequency + frequency  # Add new frequency
                knowledge.save()
        
        # Bulk create the word-source links
        if word_links_to_create:
            WordSourceLink.objects.bulk_create(word_links_to_create)
        
        # Mark source as processed
        source.processed = True
        source.save()

    def create(self, request, *args, **kwargs):
        """Override create to provide analysis data in response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the source and process words
        self.perform_create(serializer)
        source = serializer.instance
        
        # Generate analysis data for response
        content_lower = source.content.lower()
        word_list = re.findall(r'\b[a-zA-Z]+\b', content_lower)
        word_counts = Counter(word_list)
        
        total_words = sum(word_counts.values())
        unique_words = len(word_counts)
        
        if unique_words == 0:
            analysis = {
                'coverage': 100,
                'total_words': 0,
                'unique_words': 0,
                'known_words': 0,
                'new_words': 0
            }
        else:
            # Get user's known words for analysis
            user_known_words = set(UserWordKnowledge.objects.filter(
                user=request.user,
                state__in=[UserWordKnowledge.State.KNOWN, UserWordKnowledge.State.IGNORED]
            ).values_list('word__text', flat=True))
            
            # Count words by status (for analytics only - we still process all words)
            known_words_in_source = user_known_words.intersection(word_counts.keys())
            known_word_count = len(known_words_in_source)
            new_word_count = unique_words - known_word_count
            coverage = (known_word_count / unique_words * 100) if unique_words > 0 else 0
            
            analysis = {
                'coverage': round(coverage, 2),
                'total_words': total_words,
                'unique_words': unique_words,
                'known_words': known_word_count,
                'new_words': new_word_count,
                'words_processed': unique_words  # Now we process ALL words
            }
        
        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        response_data['analysis'] = analysis
        
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

class MarkWordAsKnownAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Handle both word_id (from source detail page) and word text (from dashboard)
        word_id = request.data.get("word_id")
        word_text = request.data.get("word", "").lower().strip()
        
        if word_id:
            # Source detail page sends word_id
            try:
                word = Word.objects.get(id=word_id)
            except Word.DoesNotExist:
                return Response({"error": "Word not found."}, status=status.HTTP_404_NOT_FOUND)
        elif word_text:
            # Dashboard sends word text
            word, _ = Word.objects.get_or_create(text=word_text)
        else:
            return Response({"error": "Word ID or word text is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get user profile for threshold
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        # Find or create the user's knowledge entry for this word
        knowledge, created = UserWordKnowledge.objects.get_or_create(
            user=request.user,
            word=word,
            defaults={
                'state': UserWordKnowledge.State.NEW,
                'due': timezone.now(),
                'priority': 0,
            }
        )
        
        # Update to KNOWN state with proper FSRS values
        knowledge.state = UserWordKnowledge.State.KNOWN
        knowledge.due = timezone.now() + datetime.timedelta(days=9999)  # Effectively never review again
        knowledge.last_review = timezone.now()
        knowledge.successful_reviews = max(knowledge.successful_reviews, profile.known_threshold)  # Ensure it meets threshold
        knowledge.save()
        
        return Response({
            "status": "ok",
            "word": word.text,
            "message": f"'{word.text}' has been marked as known."
        })

class ReviewWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        action = request.data.get("action")
        if action not in ["know", "dont_know"]:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        knowledge = get_object_or_404(UserWordKnowledge, pk=pk, user=request.user)
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.check_and_reset_daily_count()
        
        # Track if this is a new word being learned today
        is_new_word = knowledge.state == UserWordKnowledge.State.NEW
        if is_new_word and profile.words_learned_today < profile.daily_learning_target:
            profile.words_learned_today += 1
            profile.save()

        # Convert action to FSRS rating
        rating = 4 if action == "know" else 1
        
        # Update review count
        knowledge.review_count += 1
        
        # Calculate next review interval using FSRS
        interval_days = knowledge.calculate_next_review_interval(rating, profile.retention_rate)
        
        # Update difficulty based on performance
        knowledge.update_difficulty(rating)
        
        # Update state based on performance
        if rating == 1:  # Don't know
            knowledge.state = UserWordKnowledge.State.LEARNING
            # Schedule for re-review soon (convert hours to days)
            knowledge.due = timezone.now() + datetime.timedelta(hours=2.4)
        else:  # Know it
            if knowledge.state == UserWordKnowledge.State.NEW:
                knowledge.state = UserWordKnowledge.State.LEARNING
            
            # Check if word should be marked as KNOWN
            if knowledge.is_ready_for_known_status():
                knowledge.state = UserWordKnowledge.State.KNOWN
                # Set due date far in future for known words
                knowledge.due = timezone.now() + datetime.timedelta(days=365)
            else:
                # Schedule next review based on FSRS calculation
                knowledge.due = timezone.now() + datetime.timedelta(days=interval_days)

        knowledge.last_review = timezone.now()
        knowledge.save()

        # Calculate progress toward "known" status
        progress_info = {
            "successful_reviews": knowledge.successful_reviews,
            "threshold": profile.known_threshold,
            "reviews_remaining": max(0, profile.known_threshold - knowledge.successful_reviews),
            "stability_days": round(knowledge.stability, 1),
            "next_review_hours": round((knowledge.due - timezone.now()).total_seconds() / 3600, 1)
        }

        # Fetch the next word for the queue
        next_word_knowledge = _get_next_word(request.user, exclude_pk=knowledge.pk)
        
        return Response({
            "status": "ok", 
            "new_state": knowledge.get_state_display(),
            "new_due_date": knowledge.due.isoformat(),
            "progress": progress_info,
            "next_word": UserWordKnowledgeSerializer(next_word_knowledge).data if next_word_knowledge else None,
        })

class ChartDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        
        # Get period from query params (default to 7 days)
        period = request.GET.get('period', '7')
        if period not in ['7', '30']:
            period = '7'
        
        days_count = int(period)
        
        # Generate learning data for the requested period
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
        
        return Response({
            'period': period,
            'data': daily_learning_data,
            'total_points': len(daily_learning_data)
        })


class DeleteSourceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, source_id, *args, **kwargs):
        source = get_object_or_404(Source, id=source_id, user=request.user)
        
        with transaction.atomic():
            # Get all words linked to this source
            word_links = WordSourceLink.objects.filter(source=source).select_related('word')
            words_to_check = [link.word for link in word_links]
            
            # Statistics for user feedback
            total_words_in_source = len(words_to_check)
            words_preserved = 0
            words_deleted = 0
            
            # Delete the source (this will cascade delete WordSourceLink entries)
            source_title = source.title
            source.delete()
            
            # Check each word to see if it should be deleted
            for word in words_to_check:
                remaining_links = WordSourceLink.objects.filter(word=word).count()
                
                if remaining_links == 0:
                    # No other sources use this word, safe to delete
                    # But first, delete the UserWordKnowledge entries
                    UserWordKnowledge.objects.filter(word=word).delete()
                    word.delete()
                    words_deleted += 1
                else:
                    # Word is used in other sources, keep it
                    words_preserved += 1
                    
                    # Update priority for remaining UserWordKnowledge entries
                    for knowledge in UserWordKnowledge.objects.filter(word=word):
                        # Recalculate priority based on remaining sources
                        total_frequency = WordSourceLink.objects.filter(
                            word=word,
                            source__user=knowledge.user
                        ).aggregate(total=Sum('frequency'))['total'] or 0
                        knowledge.priority = total_frequency
                        knowledge.save()
        
        return Response({
            'message': f'Source "{source_title}" deleted successfully',
            'statistics': {
                'total_words_in_source': total_words_in_source,
                'words_preserved': words_preserved,
                'words_deleted': words_deleted,
                'explanation': f'{words_preserved} words were preserved because they appear in other sources. {words_deleted} words were completely removed.'
            }
        }, status=status.HTTP_200_OK)


# Simple debug test view
class DebugSourceTestAPIView(APIView):
    """Simple test endpoint to verify API is working"""
    permission_classes = []  # No authentication required for debug
    
    def get(self, request):
        user_info = "Anonymous" if request.user.is_anonymous else request.user.username
        return Response({
            'status': 'ok',
            'user': user_info,
            'message': 'Debug API is working',
            'timestamp': timezone.now().isoformat(),
            'server_port': '8000',
            'authentication_required': False
        })
    
    def post(self, request):
        """Echo back request data for debugging"""
        user_info = "Anonymous" if request.user.is_anonymous else request.user.username
        safe_data = {}
        
        # Log POST data safely
        if hasattr(request, 'data') and request.data:
            for key, value in request.data.items():
                if hasattr(value, 'read'):  # File object
                    safe_data[key] = {
                        'type': 'file',
                        'name': getattr(value, 'name', 'unknown'),
                        'size': getattr(value, 'size', 'unknown'),
                        'content_type': getattr(value, 'content_type', 'unknown')
                    }
                else:
                    safe_data[key] = str(value)[:200]  # Truncate long text
        
        # Log FILES data
        files_data = {}
        if hasattr(request, 'FILES') and request.FILES:
            for key, file_obj in request.FILES.items():
                files_data[key] = {
                    'name': file_obj.name,
                    'size': file_obj.size,
                    'content_type': getattr(file_obj, 'content_type', 'unknown')
                }
        
        return Response({
            'status': 'ok',
            'user': user_info,
            'request_data': safe_data,
            'request_files': files_data,
            'content_type': request.content_type,
            'method': request.method,
            'timestamp': timezone.now().isoformat(),
            'server_port': '8000',
            'authentication_required': False
        })

class UserProfileAPIView(APIView):
    """API view for user profile and learning settings."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user profile and learning settings."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        return Response({
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'date_joined': request.user.date_joined.isoformat(),
            },
            'profile': {
                'daily_new_word_target': profile.daily_new_word_target,
                'effective_daily_new_word_target': profile.get_effective_daily_new_word_target(),
                'can_modify_daily_new_word_target': profile.can_modify_daily_new_word_target(),
                'filter_stop_words': profile.filter_stop_words,
                'effective_filter_stop_words': profile.get_effective_stop_words_filter(),
                'can_modify_stop_words_filter': profile.can_modify_stop_words_filter(),
                'retention_rate': profile.retention_rate,
                'known_threshold': profile.known_threshold,
                'is_pro_active': profile.is_pro_active(),
                'words_learned_today': profile.words_learned_today,
                'last_learning_date': profile.last_learning_date.isoformat(),
            }
        })
    
    def patch(self, request):
        """Update user profile settings."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        data = request.data
        
        # Track what was changed for response
        changes = {}
        errors = {}
        
        # Handle daily_new_word_target (Pro only)
        if 'daily_new_word_target' in data:
            if not profile.can_modify_daily_new_word_target():
                errors['daily_new_word_target'] = "Upgrade to Pro to customize daily new word target"
            else:
                try:
                    new_target = int(data['daily_new_word_target'])
                    if 5 <= new_target <= 100:
                        old_value = profile.daily_new_word_target
                        profile.daily_new_word_target = new_target
                        changes['daily_new_word_target'] = {
                            'old': old_value,
                            'new': new_target
                        }
                    else:
                        errors['daily_new_word_target'] = "Daily new word target must be between 5 and 100"
                except (ValueError, TypeError):
                    errors['daily_new_word_target'] = "Invalid value for daily new word target"
        
        # Handle filter_stop_words (Pro only)
        if 'filter_stop_words' in data:
            if not profile.can_modify_stop_words_filter():
                errors['filter_stop_words'] = "Upgrade to Pro to customize stop words filtering"
            else:
                try:
                    new_setting = bool(data['filter_stop_words'])
                    old_value = profile.filter_stop_words
                    profile.filter_stop_words = new_setting
                    changes['filter_stop_words'] = {
                        'old': old_value,
                        'new': new_setting
                    }
                except (ValueError, TypeError):
                    errors['filter_stop_words'] = "Invalid value for stop words filtering"
        
        # Handle retention_rate
        if 'retention_rate' in data:
            try:
                new_rate = float(data['retention_rate'])
                if 0.8 <= new_rate <= 0.95:
                    old_value = profile.retention_rate
                    profile.retention_rate = new_rate
                    changes['retention_rate'] = {
                        'old': old_value,
                        'new': new_rate
                    }
                else:
                    errors['retention_rate'] = "Retention rate must be between 0.8 and 0.95"
            except (ValueError, TypeError):
                errors['retention_rate'] = "Invalid value for retention rate"
        
        # Handle known_threshold
        if 'known_threshold' in data:
            try:
                new_threshold = int(data['known_threshold'])
                if 3 <= new_threshold <= 10:
                    old_value = profile.known_threshold
                    profile.known_threshold = new_threshold
                    changes['known_threshold'] = {
                        'old': old_value,
                        'new': new_threshold
                    }
                else:
                    errors['known_threshold'] = "Known threshold must be between 3 and 10"
            except (ValueError, TypeError):
                errors['known_threshold'] = "Invalid value for known threshold"
        
        # Save changes if any
        if changes and not errors:
            profile.save()
            
        response_data = {
            'status': 'success' if changes and not errors else 'error',
            'changes': changes,
            'errors': errors,
            'profile': {
                'daily_new_word_target': profile.daily_new_word_target,
                'effective_daily_new_word_target': profile.get_effective_daily_new_word_target(),
                'can_modify_daily_new_word_target': profile.can_modify_daily_new_word_target(),
                'filter_stop_words': profile.filter_stop_words,
                'effective_filter_stop_words': profile.get_effective_stop_words_filter(),
                'can_modify_stop_words_filter': profile.can_modify_stop_words_filter(),
                'retention_rate': profile.retention_rate,
                'known_threshold': profile.known_threshold,
                'is_pro_active': profile.is_pro_active(),
            }
        }
        
        status_code = status.HTTP_200_OK if not errors else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=status_code)

 