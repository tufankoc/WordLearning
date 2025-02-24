from django.test import TestCase
from django.contrib.auth.models import User
from words.models import Word, ReviewLog
from datetime import datetime

class WordModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_word_creation(self):
        """Test kelime oluşturma"""
        word = Word.objects.create(
            user=self.user,
            text='test',
            frequency=1,
            status=0
        )
        self.assertEqual(word.text, 'test')
        self.assertEqual(word.frequency, 1)
        self.assertEqual(word.status, 0)
        self.assertEqual(word.user, self.user)

    def test_word_str_method(self):
        """Test kelime string temsili"""
        word = Word.objects.create(
            user=self.user,
            text='test',
            frequency=1
        )
        self.assertEqual(str(word), 'test')

class ReviewLogModelTests(TestCase):
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

    def test_review_log_creation(self):
        """Test tekrar kaydı oluşturma"""
        review_log = ReviewLog.objects.create(
            user=self.user,
            word=self.word,
            result=True
        )
        self.assertEqual(review_log.user, self.user)
        self.assertEqual(review_log.word, self.word)
        self.assertTrue(review_log.result)
        self.assertIsNotNone(review_log.review_date)

    def test_review_log_str_method(self):
        """Test tekrar kaydı string temsili"""
        review_log = ReviewLog.objects.create(
            user=self.user,
            word=self.word,
            result=True
        )
        expected_str = f"{self.word.text} - {review_log.review_date}"
        self.assertEqual(str(review_log), expected_str) 