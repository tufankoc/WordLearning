from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .models import Source, Word, UserWordKnowledge

class EnhancedSourceSerializer(serializers.ModelSerializer):
    # File upload fields
    pdf_file = serializers.FileField(required=False, write_only=True)
    srt_file = serializers.FileField(required=False, write_only=True)
    
    # URL fields
    web_url = serializers.URLField(required=False, write_only=True)
    youtube_url = serializers.URLField(required=False, write_only=True)
    
    # Manual text input
    manual_text = serializers.CharField(required=False, write_only=True)
    
    # Read-only fields for response
    analysis = serializers.DictField(read_only=True)
    content_preview = serializers.CharField(read_only=True)
    
    class Meta:
        model = Source
        fields = [
            'id', 'title', 'source_type', 'content', 'created_at',
            'pdf_file', 'srt_file', 'web_url', 'youtube_url', 'manual_text',
            'analysis', 'content_preview'
        ]
        read_only_fields = ['user', 'content', 'source_type']
        
    def validate(self, data):
        """
        Validate that exactly one input type is provided.
        """
        input_fields = ['pdf_file', 'srt_file', 'web_url', 'youtube_url', 'manual_text']
        provided_inputs = [field for field in input_fields if data.get(field)]
        
        if len(provided_inputs) != 1:
            raise serializers.ValidationError(
                "Exactly one input type must be provided: pdf_file, srt_file, web_url, youtube_url, or manual_text"
            )
        
        # Validate file types
        if 'pdf_file' in provided_inputs:
            pdf_file = data['pdf_file']
            if not pdf_file.name.lower().endswith('.pdf'):
                raise serializers.ValidationError("PDF file must have .pdf extension")
            
        if 'srt_file' in provided_inputs:
            srt_file = data['srt_file']
            if not srt_file.name.lower().endswith('.srt'):
                raise serializers.ValidationError("Subtitle file must have .srt extension")
        
        # Validate YouTube URL format
        if 'youtube_url' in provided_inputs:
            from .content_parsers import extract_youtube_video_id
            youtube_url = data['youtube_url']
            if not extract_youtube_video_id(youtube_url):
                raise serializers.ValidationError("Invalid YouTube URL format")
        
        # Validate manual text length
        if 'manual_text' in provided_inputs:
            manual_text = data['manual_text']
            if len(manual_text.strip()) < 10:
                raise serializers.ValidationError("Manual text must be at least 10 characters long")
        
        return data
    
    def validate_title(self, value):
        """Validate title length and content."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Title must be at least 2 characters long")
        if len(value) > 255:
            raise serializers.ValidationError("Title must be less than 255 characters")
        return value.strip()
    
    def create(self, validated_data):
        """Custom create method to handle input fields that don't belong to Source model."""
        # Remove input fields that don't belong to Source model
        input_fields = ['pdf_file', 'srt_file', 'web_url', 'youtube_url', 'manual_text']
        for field in input_fields:
            validated_data.pop(field, None)
        
        # Create source with only model fields
        return Source.objects.create(**validated_data)

class SourceSerializer(serializers.ModelSerializer):
    """Legacy serializer for backward compatibility."""
    class Meta:
        model = Source
        fields = ['id', 'title', 'source_type', 'content', 'created_at']
        read_only_fields = ['user']

class WordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = [
            'id', 'text', 'definition', 'translation_tr',
            'part_of_speech', 'phonetic', 'audio_url', 'example_sentence',
            'synonyms', 'antonyms'
        ]

class UserWordKnowledgeSerializer(serializers.ModelSerializer):
    word = WordSerializer(read_only=True)
    successful_reviews = serializers.IntegerField(read_only=True)
    threshold = serializers.SerializerMethodField()
    reviews_remaining = serializers.SerializerMethodField()

    class Meta:
        model = UserWordKnowledge
        fields = [
            'id', 'word', 'state', 'due', 'stability', 'difficulty', 'lapses', 
            'last_review', 'priority', 'review_count', 'successful_reviews',
            'threshold', 'reviews_remaining'
        ]
    
    def get_threshold(self, obj):
        """Get the user's known threshold setting."""
        return obj.user.profile.known_threshold
    
    def get_reviews_remaining(self, obj):
        """Calculate how many more successful reviews are needed."""
        threshold = obj.user.profile.known_threshold
        return max(0, threshold - obj.successful_reviews) 