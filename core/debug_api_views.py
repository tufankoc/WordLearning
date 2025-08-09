"""
Debug and Enhanced Source Extraction API Views
Comprehensive implementation with logging, error handling, and proper routing
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from .models import Source, Word, WordSourceLink, UserWordKnowledge, UserProfile
from .serializers import EnhancedSourceSerializer
from .content_parsers import (
    CONTENT_PARSERS, 
    ContentParsingError, 
    SecurityError,
    get_content_preview
)
from rest_framework.views import APIView
import datetime
import re
from collections import Counter
import logging

# Enhanced logging setup
logger = logging.getLogger(__name__)

class DebugEnhancedSourceCreateAPIView(generics.CreateAPIView):
    """
    Debug version of Enhanced source creation with comprehensive logging and error handling.
    """
    serializer_class = EnhancedSourceSerializer
    permission_classes = [IsAuthenticated]

    def _log_request_data(self, request):
        """Log request data for debugging"""
        logger.info(f"=== SOURCE EXTRACTION DEBUG ===")
        logger.info(f"User: {request.user.id} ({request.user.username})")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        
        # Log POST data (excluding file contents)
        if hasattr(request, 'data') and request.data:
            safe_data = {}
            for key, value in request.data.items():
                if hasattr(value, 'read'):  # File object
                    safe_data[key] = f"<File: {getattr(value, 'name', 'unknown')} - {getattr(value, 'size', 'unknown')} bytes>"
                else:
                    safe_data[key] = str(value)[:100]  # Truncate long text
            logger.info(f"Request data: {safe_data}")
        
        # Log FILES data
        if hasattr(request, 'FILES') and request.FILES:
            files_info = {}
            for key, file_obj in request.FILES.items():
                files_info[key] = {
                    'name': file_obj.name,
                    'size': file_obj.size,
                    'content_type': getattr(file_obj, 'content_type', 'unknown')
                }
            logger.info(f"Request files: {files_info}")

    def _determine_source_type_and_extract_content(self, validated_data):
        """
        Enhanced content extraction with comprehensive debugging and error handling.
        
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
        """Enhanced perform_create with comprehensive error handling."""
        user = self.request.user
        
        # Log request data
        self._log_request_data(self.request)
        
        # Check Pro account limits
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
        """Enhanced word processing with logging."""
        logger.info(f"=== WORD PROCESSING START for source {source.id} ===")
        
        # 1. Tokenize the content
        content_lower = source.content.lower()
        word_list = re.findall(r'\b[a-zA-Z]+\b', content_lower)
        word_counts = Counter(word_list)
        
        logger.info(f"Tokenization results:")
        logger.info(f"  - Total words: {len(word_list)}")
        logger.info(f"  - Unique words: {len(word_counts)}")
        logger.info(f"  - Top 10 frequent: {dict(word_counts.most_common(10))}")
        
        if not word_counts:
            logger.warning("No words found in content")
            source.processed = True
            source.save()
            return 0
        
        # 2. Process each word
        words_to_process = []
        words_created = 0
        
        for word_text, frequency in word_counts.items():
            # Create or get the Word object
            word, created = Word.objects.get_or_create(text=word_text)
            if created:
                words_created += 1
                logger.debug(f"Created new word: {word_text}")
            
            # Fetch definition for new words (in background/async if possible)
            if created and not word.definition:
                try:
                    from .utils import fetch_word_definition
                    word.definition = fetch_word_definition(word_text)
                    word.save()
                    logger.debug(f"Fetched definition for: {word_text}")
                except Exception as e:
                    logger.warning(f"Failed to fetch definition for {word_text}: {e}")
            
            words_to_process.append((word, frequency))
        
        logger.info(f"Created {words_created} new word objects")
        
        # 3. Create WordSourceLink entries
        word_links_to_create = []
        knowledge_created = 0
        knowledge_updated = 0
        
        for word, frequency in words_to_process:
            # Create the link between word, source, and user with frequency
            word_links_to_create.append(
                WordSourceLink(
                    word=word, 
                    source=source, 
                    frequency=frequency
                )
            )
            
            # Create or update UserWordKnowledge
            knowledge, created = UserWordKnowledge.objects.get_or_create(
                user=user,
                word=word,
                defaults={
                    'state': UserWordKnowledge.State.NEW,
                    'due': timezone.now(),
                    'priority': frequency,
                }
            )
            
            if created:
                knowledge_created += 1
            else:
                # Update priority if knowledge already existed
                total_frequency = WordSourceLink.objects.filter(
                    word=word,
                    source__user=user
                ).aggregate(total=Sum('frequency'))['total'] or 0
                knowledge.priority = total_frequency + frequency
                knowledge.save()
                knowledge_updated += 1
        
        # Bulk create the word-source links
        if word_links_to_create:
            WordSourceLink.objects.bulk_create(word_links_to_create)
            logger.info(f"Created {len(word_links_to_create)} word-source links")
        
        logger.info(f"Knowledge entries: {knowledge_created} created, {knowledge_updated} updated")
        
        # Mark source as processed
        source.processed = True
        source.save()
        
        logger.info(f"=== WORD PROCESSING END ===")
        return len(word_counts)

    def create(self, request, *args, **kwargs):
        """Enhanced create method with comprehensive response data."""
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
            
            # Enhanced response format
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
            logger.info(f"Response data: {response_data}")
            
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"=== API REQUEST FAILED ===")
            logger.error(f"Error: {str(e)}", exc_info=True)
            raise


# Simple test view for debugging
class DebugSourceTestAPIView(APIView):
    """Simple test endpoint to verify API is working"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'status': 'ok',
            'user': request.user.username,
            'message': 'Debug API is working',
            'timestamp': timezone.now().isoformat()
        })
    
    def post(self, request):
        """Echo back request data for debugging"""
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
            'user': request.user.username,
            'request_data': safe_data,
            'request_files': files_data,
            'content_type': request.content_type,
            'method': request.method,
            'timestamp': timezone.now().isoformat()
        }) 