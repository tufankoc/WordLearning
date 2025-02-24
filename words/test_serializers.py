from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from words.models import Word, ReviewLog
from words.serializers import WordSerializer, ReviewLogSerializer

class WordSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user

    def test_word_serialization(self):
        """Test kelime serileştirme"""
        word = Word.objects.create(
            user=self.user,
            text='test',
            frequency=1,
            status=0
        )
        serializer = WordSerializer(word)
        self.assertEqual(serializer.data['text'], 'test')
        self.assertEqual(serializer.data['frequency'], 1)
        self.assertEqual(serializer.data['status'], 0)

    def test_word_deserialization(self):
        """Test kelime deserileştirme"""
        data = {
            'text': 'test',
            'status': 0
        }
        serializer = WordSerializer(data=data, context={'request': self.request})
        self.assertTrue(serializer.is_valid())
        word = serializer.save()
        self.assertEqual(word.text, 'test')
        self.assertEqual(word.status, 0)
        self.assertEqual(word.user, self.user)

class ReviewLogSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.word = Word.objects.create(
            user=self.user,
            text='test',
            frequency=1
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user

    def test_review_log_serialization(self):
        """Test tekrar kaydı serileştirme"""
        review_log = ReviewLog.objects.create(
            user=self.user,
            word=self.word,
            result=True
        )
        serializer = ReviewLogSerializer(review_log)
        self.assertEqual(serializer.data['word'], self.word.id)
        self.assertTrue(serializer.data['result'])

    def test_review_log_deserialization(self):
        """Test tekrar kaydı deserileştirme"""
        data = {
            'word': self.word.id,
            'result': True
        }
        serializer = ReviewLogSerializer(data=data, context={'request': self.request})
        self.assertTrue(serializer.is_valid())
        review_log = serializer.save()
        self.assertEqual(review_log.word, self.word)
        self.assertTrue(review_log.result)
        self.assertEqual(review_log.user, self.user) 