from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Word, ReviewLog, TextAnalysis, TextCategory, DictionaryWord, DictionaryReport

class WordSerializer(serializers.ModelSerializer):
    translation = serializers.SerializerMethodField()
    dictionary_word_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Word
        fields = ['id', 'text', 'translation', 'frequency', 'status', 'last_review', 'next_review', 'dictionary_word_id']
        read_only_fields = ['frequency', 'status', 'last_review', 'next_review']

    def get_translation(self, obj):
        try:
            if hasattr(obj, 'dictionary_word') and obj.dictionary_word and obj.dictionary_word.translation:
                return obj.dictionary_word.translation.strip()
            return None
        except Exception as e:
            print(f"Translation error for word {obj.text}: {str(e)}")
            return None

    def create(self, validated_data):
        user = self.context['request'].user
        text = validated_data.get('text')
        dictionary_word_id = validated_data.pop('dictionary_word_id', None)

        try:
            # Önce sözlükte kelimeyi ara
            if dictionary_word_id:
                dictionary_word = DictionaryWord.objects.get(id=dictionary_word_id)
            else:
                dictionary_word = DictionaryWord.objects.filter(text=text).first()

            # Kelimeyi bul veya oluştur
            word, created = Word.objects.get_or_create(
                user=user,
                text=text,
                defaults={
                    'dictionary_word': dictionary_word,
                    'frequency': validated_data.get('frequency', 1)
                }
            )

            # Eğer kelime varsa ve dictionary_word değişmişse güncelle
            if not created and dictionary_word and word.dictionary_word != dictionary_word:
                word.dictionary_word = dictionary_word
                word.save()

            return word
        except DictionaryWord.DoesNotExist:
            # Sözlük kelimesi bulunamazsa normal kelime olarak oluştur
            return super().create(validated_data)

class ReviewLogSerializer(serializers.ModelSerializer):
    difficulty = serializers.ChoiceField(choices=Word.DIFFICULTY_CHOICES)

    class Meta:
        model = ReviewLog
        fields = ['id', 'word', 'review_date', 'result', 'difficulty']
        read_only_fields = ['review_date']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']  # Bu alanlar değiştirilemez

class TextCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TextCategory
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class TextAnalysisSerializer(serializers.ModelSerializer):
    words = WordSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = TextAnalysis
        fields = [
            'id', 'title', 'category', 'category_name', 'type', 'total_words', 'known_words',
            'comprehension_rate', 'total_pages', 'created_at',
            'words', 'content'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class DictionaryWordSerializer(serializers.ModelSerializer):
    added_by_username = serializers.CharField(source='added_by.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)
    report_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DictionaryWord
        fields = [
            'id', 'text', 'translation', 'frequency', 'created_at', 'updated_at',
            'is_verified', 'verified_at', 'verified_by_username', 'added_by_username',
            'report_count'
        ]
        read_only_fields = ['frequency', 'is_verified', 'verified_at', 'verified_by', 'report_count']

class DictionaryWordCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictionaryWord
        fields = ['id', 'text', 'translation']

class DictionaryReportSerializer(serializers.ModelSerializer):
    reported_by_username = serializers.CharField(source='reported_by.username', read_only=True)
    word_text = serializers.CharField(source='word.text', read_only=True)

    class Meta:
        model = DictionaryReport
        fields = [
            'id', 'word', 'word_text', 'reason', 'created_at', 'status',
            'reported_by_username', 'resolved_at'
        ]
        read_only_fields = ['status', 'resolved_at'] 