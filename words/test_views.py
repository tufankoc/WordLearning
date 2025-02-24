from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from words.models import Word, ReviewLog
from datetime import datetime, timedelta

class WordViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_process_text(self):
        """Test metin işleme endpoint'i"""
        url = reverse('word-process-text')
        data = {'text': 'bu bir test metnidir test'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Word.objects.count(), 4)  # 'bu', 'bir', 'test', 'metnidir'
        self.assertEqual(Word.objects.get(text='test').frequency, 2)

    def test_daily_review(self):
        """Test günlük tekrar listesi endpoint'i"""
        # Test için kelimeler oluştur
        words = [
            Word.objects.create(
                user=self.user,
                text=f'word{i}',
                frequency=i,
                next_review=datetime.now().date()
            ) for i in range(5)
        ]

        url = reverse('word-daily-review')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

class ReviewLogViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.word = Word.objects.create(
            user=self.user,
            text='test',
            frequency=1
        )

    def test_create_review_log(self):
        """Test kelime tekrar kaydı oluşturma"""
        url = reverse('review-list')
        data = {
            'word': self.word.id,
            'result': True
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReviewLog.objects.count(), 1)
        self.assertEqual(ReviewLog.objects.get().result, True)

        # Kelime durumunun güncellendiğini kontrol et
        self.word.refresh_from_db()
        self.assertEqual(self.word.status, 1)  # Status artmış olmalı
        self.assertIsNotNone(self.word.next_review)  # Sonraki tekrar tarihi ayarlanmış olmalı 