from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from nltk.tokenize import word_tokenize
from collections import Counter
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
import PyPDF2
import io
import time
import re
import string
from .models import Word, ReviewLog, TextAnalysis, UserProfile, CommonWord, TextCategory, DictionaryWord
from .serializers import WordSerializer, ReviewLogSerializer, UserProfileSerializer, TextAnalysisSerializer, TextCategorySerializer
import requests
from bs4 import BeautifulSoup
from django.http import HttpResponse
from django.db.models import F
from django.db.utils import IntegrityError
import random

# Create your views here.

def is_valid_word(word):
    """
    Kelimenin geçerli olup olmadığını kontrol eder.
    Kelime küçük harfle gelir ve sadece harf içeren kelimeler kabul edilir.
    """
    # Kelime sadece harflerden oluşmalı ve en az 2 karakter olmalı
    return word.isalpha() and len(word) >= 2

def process_word(user, word, frequency=1):
    """
    Kelimeyi işler ve veritabanına kaydeder.
    Kelime zaten küçük harfle geldiği için ek bir dönüşüm yapmaya gerek yok.
    """
    try:
        # Önce sözlükte kelimeyi ara
        dictionary_word = DictionaryWord.objects.filter(text=word).first()

        # Kelimeyi bul veya oluştur
        word_obj, created = Word.objects.get_or_create(
            user=user,
            text=word,
            defaults={
                'frequency': frequency,
                'status': 0,  # Hiç çalışılmadı
                'dictionary_word': dictionary_word  # Sözlük kelimesini bağla
            }
        )

        # Eğer kelime daha önce oluşturulmuşsa, frekansı güncelle
        if not created:
            word_obj.frequency += frequency
            # Eğer sözlük kelimesi varsa ve henüz bağlanmamışsa, bağla
            if dictionary_word and not word_obj.dictionary_word:
                word_obj.dictionary_word = dictionary_word
            word_obj.save()

        return word_obj
    except Exception as e:
        print(f"Kelime işlenirken hata: {str(e)}")
        return None

class TextCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = TextCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TextCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def default_categories(self, request):
        # Varsayılan kategorileri oluştur
        default_categories = ['Makale', 'Hikaye', 'Haber', 'Kitap', 'Blog', 'Akademik', 'Teknik', 'Eğitim']
        created_categories = []
        
        for category_name in default_categories:
            category, created = TextCategory.objects.get_or_create(
                user=request.user,
                name=category_name
            )
            if created:
                created_categories.append(category_name)
        
        return Response({
            'message': f"{len(created_categories)} varsayılan kategori eklendi" if created_categories else "Tüm varsayılan kategoriler zaten mevcut",
            'created_categories': created_categories
        })

class WordViewSet(viewsets.ModelViewSet):
    serializer_class = WordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # dictionary_word ilişkisini önceden yükle
        queryset = Word.objects.filter(user=self.request.user).select_related('dictionary_word')

        # Filtreleme parametrelerini al
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        translation = self.request.query_params.get('translation')
        sort = self.request.query_params.get('sort', 'text')
        order = self.request.query_params.get('order', 'asc')

        # Status filtresi
        if status is not None:
            queryset = queryset.filter(status=status)

        # Arama filtresi
        if search:
            queryset = queryset.filter(text__icontains=search)

        # Çeviri filtresi
        if translation == 'with':
            queryset = queryset.filter(dictionary_word__isnull=False).exclude(dictionary_word__translation='')
        elif translation == 'without':
            queryset = queryset.filter(Q(dictionary_word__isnull=True) | Q(dictionary_word__translation=''))

        # Sıralama
        order_prefix = '-' if order == 'desc' else ''
        if sort == 'text':
            queryset = queryset.order_by(f'{order_prefix}text')
        elif sort == 'frequency':
            queryset = queryset.order_by(f'{order_prefix}frequency')
        elif sort == 'status':
            queryset = queryset.order_by(f'{order_prefix}status')
        elif sort == 'last_review':
            queryset = queryset.order_by(f'{order_prefix}last_review')
        elif sort == 'next_review':
            queryset = queryset.order_by(f'{order_prefix}next_review')

        return queryset

    def process_word(self, word):
        # Önce sözlükte kelimeyi ara
        dictionary_word = DictionaryWord.objects.filter(text=word).first()
        
        # Kullanıcının kelime listesinde bu kelime var mı kontrol et
        user_word = Word.objects.filter(user=self.request.user, text=word).first()
        
        if user_word:
            # Kelime zaten varsa, sözlük referansını güncelle
            if dictionary_word and user_word.dictionary_word != dictionary_word:
                user_word.dictionary_word = dictionary_word
                user_word.save()
            return user_word
        else:
            # Yeni kelime oluştur
            return Word.objects.create(
                user=self.request.user,
                text=word,
                dictionary_word=dictionary_word
            )

    def process_text(self, request):
        try:
            text = request.data.get('text', '').strip()
            if not text:
                return Response({'error': 'Text is required'}, status=400)

            # Metni kelimelere ayır
            words = word_tokenize(text.lower())
            processed_words = []
            word_freq = Counter([word for word in words if is_valid_word(word)])

            for word, freq in word_freq.items():
                # Önce global sözlükte kelimeyi ara
                dictionary_word = DictionaryWord.objects.filter(text=word).first()

                # Kullanıcının kelime listesine ekle
                word_obj, created = Word.objects.get_or_create(
                    user=request.user,
                    text=word,
                    defaults={
                        'frequency': freq,
                        'status': 0,  # Hiç çalışılmadı
                        'dictionary_word': dictionary_word  # Global sözlük bağlantısı
                    }
                )

                if not created:
                    # Kelime zaten varsa frekansı güncelle
                    word_obj.frequency += freq
                    # Global sözlük bağlantısını güncelle
                    if dictionary_word and not word_obj.dictionary_word:
                        word_obj.dictionary_word = dictionary_word
                    word_obj.save()

                processed_words.append(word_obj)

            serializer = self.get_serializer(processed_words, many=True)
            return Response(serializer.data)

        except Exception as e:
            print(f"Error processing text: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def text_analyses(self, request):
        analyses = TextAnalysis.objects.filter(user=request.user)
        
        # Her analiz için bilinen kelimeleri yeniden hesapla
        for analysis in analyses:
            # Metindeki geçerli kelimeleri bul
            if analysis.content:  # İçerik varsa işle
                words = word_tokenize(analysis.content.lower())
                valid_words = [word for word in words if is_valid_word(word)]
                total_words = len(valid_words)
                
                # Tam öğrenilen kelimeleri say (status = 3)
                known_words = Word.objects.filter(
                    user=request.user,
                    text__in=valid_words,
                    status=3  # Sadece tam öğrenilmiş kelimeler
                ).count()
                
                # Az bilinen kelimeleri say (status = 2)
                partially_known = Word.objects.filter(
                    user=request.user,
                    text__in=valid_words,
                    status=2  # Az bilinen kelimeler
                ).count()
                
                # Anlama oranını hesapla (tam öğrenilen + az bilinenin yarısı)
                comprehension_rate = ((known_words + (partially_known * 0.5)) / total_words * 100) if total_words > 0 else 0
                
                # Analizi güncelle
                analysis.known_words = known_words  # Sadece tam öğrenilenleri kaydet
                analysis.comprehension_rate = round(comprehension_rate, 2)
                analysis.save()
        
        serializer = TextAnalysisSerializer(analyses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def process_pdf(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)

        pdf_file = request.FILES['file']
        if not pdf_file.name.endswith('.pdf'):
            return Response({'error': 'Only PDF files are allowed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # PDF'i oku
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
            text = ''
            total_words = 0
            known_words = 0
            processed_words = []

            # Her sayfayı işle
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                text += page_text + ' '

            # Tüm metni işle
            words = word_tokenize(text.lower())
            # Geçerli kelimeleri filtrele
            valid_words = [word for word in words if is_valid_word(word)]
            word_freq = Counter(valid_words)
            total_words = len(valid_words)

            # Bilinen kelimeleri say (sadece Türkçe anlamı olanlar)
            known_words = Word.objects.filter(
                user=request.user,
                text__in=valid_words,
                status__in=[2, 3],  # Az Biliniyor ve Tam öğrenildi
                translation__isnull=False  # Türkçe anlamı olanlar
            ).exclude(
                translation=''  # Boş çevirisi olanları hariç tut
            ).count()

            # Her kelime için veritabanını güncelle
            for word, freq in word_freq.items():
                word_obj = process_word(request.user, word, freq)
                if word_obj:  # None değilse ekle
                    processed_words.append(word_obj)

            # Bilinen kelime oranını hesapla
            comprehension_rate = (known_words / total_words * 100) if total_words > 0 else 0

            # Analiz kaydını oluştur
            analysis = TextAnalysis.objects.create(
                user=request.user,
                title=f"PDF Analizi - {pdf_file.name}",
                type='pdf',
                total_words=total_words,
                known_words=known_words,
                comprehension_rate=round(comprehension_rate, 2),
                total_pages=len(pdf_reader.pages),
                content=text  # Orijinal metni kaydet
            )
            analysis.words.set(processed_words)

            return Response({
                'message': 'PDF processed successfully',
                'total_words': total_words,
                'known_words': known_words,
                'comprehension_rate': round(comprehension_rate, 2),
                'total_pages': len(pdf_reader.pages)
            })

        except Exception as e:
            return Response(
                {'error': f'Error processing PDF: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def daily_review(self, request):
        today = timezone.now().date()
        
        # Bugün tekrar edilmesi gereken kelimeler veya hiç çalışılmamış kelimeler
        words_to_review = Word.objects.filter(
            user=request.user
        ).filter(
            Q(next_review__lte=today) | Q(next_review__isnull=True)
        ).order_by('-frequency')  # En sık kullanılan kelimeler önce

        serializer = self.get_serializer(words_to_review, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        # Kullanıcının tüm analizlerindeki kelimeleri al
        analyses = TextAnalysis.objects.filter(user=request.user)
        all_words = set()
        
        for analysis in analyses:
            if analysis.content:
                words = word_tokenize(analysis.content.lower())
                valid_words = [word for word in words if is_valid_word(word)]
                all_words.update(valid_words)
        
        # Sadece metinlerde geçen kelimeleri filtrele
        words = Word.objects.filter(
            user=request.user,
            text__in=all_words
        )
        
        total = len(all_words)  # Toplam benzersiz kelime sayısı
        not_studied = words.filter(status=0).count()
        learning = words.filter(status=1).count()
        partially_known = words.filter(status=2).count()
        known = words.filter(status=3).count()
        
        return Response({
            'total': total,
            'not_studied': not_studied,
            'learning': learning,
            'partially_known': partially_known,
            'known': known,
            'progress': round((known / total * 100), 2) if total > 0 else 0
        })

    @action(detail=False, methods=['get'])
    def daily_progress(self, request):
        today = timezone.now().date()
        last_week = today - timedelta(days=7)
        
        reviews = ReviewLog.objects.filter(
            user=request.user,
            review_date__date__gte=last_week
        ).values('review_date__date').annotate(
            correct=Count('id', filter=Q(result=True)),
            incorrect=Count('id', filter=Q(result=False))
        ).order_by('review_date__date')

        # Son 7 günün verilerini hazırla
        result = []
        current = last_week
        while current <= today:
            day_data = next(
                (r for r in reviews if r['review_date__date'] == current),
                {'correct': 0, 'incorrect': 0}
            )
            result.append({
                'date': current.strftime('%Y-%m-%d'),
                'correct': day_data['correct'],
                'incorrect': day_data['incorrect']
            })
            current += timedelta(days=1)

        return Response(result)

    @action(detail=False, methods=['post'])
    def update_translations(self, request):
        translations = request.data.get('translations', [])
        if not translations:
            return Response({'error': 'Çeviri listesi boş'}, status=400)
            
        added_count = 0
        updated_count = 0
        
        for item in translations:
            text = item.get('text', '').strip().lower()
            translation = item.get('translation', '').strip()
            
            if text and translation and is_valid_word(text):
                try:
                    # Sözlük tablosunda kelimeyi ara veya oluştur
                    dictionary_word, created = DictionaryWord.objects.get_or_create(
                        text=text,
                        defaults={
                            'translation': translation,
                            'added_by': request.user
                        }
                    )
                    
                    # Eğer kelime varsa ve çevirisi farklıysa güncelle
                    if not created and dictionary_word.translation != translation:
                        dictionary_word.translation = translation
                        dictionary_word.updated_at = timezone.now()
                        dictionary_word.save()
                        updated_count += 1
                    elif created:
                        added_count += 1

                    # Tüm kullanıcıların kelime listelerini güncelle
                    Word.objects.filter(text=text).update(dictionary_word=dictionary_word)

                    # Mevcut kullanıcının kelime listesine ekle
                    word, word_created = Word.objects.get_or_create(
                        user=request.user,
                        text=text,
                        defaults={
                            'dictionary_word': dictionary_word,
                            'frequency': 1
                        }
                    )

                    # Eğer kelime zaten varsa dictionary_word'ü güncelle
                    if not word_created and word.dictionary_word != dictionary_word:
                        word.dictionary_word = dictionary_word
                        word.save()

                except Exception as e:
                    print(f"Kelime işlenirken hata: {str(e)}")
                    continue

        return Response({
            'message': f'{added_count} yeni kelime eklendi, {updated_count} kelime güncellendi',
            'added_count': added_count,
            'updated_count': updated_count
        })

    @action(detail=False, methods=['get'])
    def export_words(self, request):
        # Filtreleme parametrelerini al
        status = request.query_params.get('status')
        search = request.query_params.get('search')
        sort = request.query_params.get('sort', 'text')
        order = request.query_params.get('order', 'asc')
        translation_filter = request.query_params.get('translation')  # 'with', 'without', None (all)

        # Temel sorgu
        queryset = Word.objects.filter(user=request.user).select_related('dictionary_word')

        # Filtreleri uygula
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(text__icontains=search)
        if translation_filter == 'with':
            queryset = queryset.filter(dictionary_word__isnull=False).exclude(dictionary_word__translation='')
        elif translation_filter == 'without':
            queryset = queryset.filter(Q(dictionary_word__isnull=True) | Q(dictionary_word__translation=''))

        # Sıralamayı uygula
        order_prefix = '-' if order == 'desc' else ''
        queryset = queryset.order_by(f'{order_prefix}{sort}')

        # Excel formatında dışa aktarma isteniyorsa
        if request.query_params.get('export') == 'excel':
            import xlsxwriter
            import io

            # Excel dosyası oluştur
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()

            # Başlıkları yaz
            headers = ['Kelime', 'Türkçe Anlamı', 'Sıklık', 'Durum', 'Son Tekrar', 'Sonraki Tekrar']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)

            # Verileri yaz
            for row, word in enumerate(queryset, start=1):
                status_map = {0: 'Hiç Çalışılmadı', 1: 'Bilinemedi', 
                            2: 'Az Biliniyor', 3: 'Tam Öğrenildi'}
                worksheet.write(row, 0, word.text)
                worksheet.write(row, 1, word.dictionary_word.translation if word.dictionary_word else '')
                worksheet.write(row, 2, word.frequency)
                worksheet.write(row, 3, status_map.get(word.status, ''))
                worksheet.write(row, 4, word.last_review.strftime('%Y-%m-%d %H:%M') if word.last_review else '')
                worksheet.write(row, 5, word.next_review.strftime('%Y-%m-%d %H:%M') if word.next_review else '')

            workbook.close()
            output.seek(0)

            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=kelimelerim.xlsx'
            return response

        # Normal API yanıtı için
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class ReviewLogViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReviewLog.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        word = serializer.validated_data['word']
        difficulty = serializer.validated_data['difficulty']
        result = serializer.validated_data['result']

        # Kelime durumunu güncelle
        if difficulty <= 2:  # Çok Zor veya Zor
            word.status = 1  # Bilinemedi
            word.consecutive_correct = 0
            word.interval = max(60, word.interval // 2)  # Aralığı yarıya düşür (minimum 1 saat)
        elif difficulty == 3:  # Orta
            word.consecutive_correct += 1 if result else 0
            if word.consecutive_correct >= 2:
                word.status = 2  # Az Biliniyor
            word.interval = word.interval * 1.5  # 1.5 kat artış
        else:  # Kolay veya Çok Kolay
            word.consecutive_correct += 1
            if word.consecutive_correct >= 4:
                word.status = 3  # Tam Öğrenildi
            elif word.consecutive_correct >= 2:
                word.status = 2  # Az Biliniyor
            word.interval = word.interval * 2  # 2 kat artış

        # İlk tekrarlar için özel aralıklar
        if word.review_count == 0:
            word.interval = 60  # İlk tekrar: 1 saat
        elif word.review_count == 1:
            word.interval = 60 * 24  # İkinci tekrar: 1 gün
        elif word.review_count == 2:
            word.interval = 60 * 24 * 3  # Üçüncü tekrar: 3 gün
        elif word.review_count == 3:
            word.interval = 60 * 24 * 7  # Dördüncü tekrar: 1 hafta

        word.last_review = timezone.now()
        word.next_review = timezone.now() + timedelta(minutes=word.interval)
        word.review_count += 1
        word.save()

        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def due_reviews(self, request):
        try:
            now = timezone.now()
            today = now.date()
            
            # Kullanıcının yüklediği metinlerdeki kelimeleri al
            user_text_words = set()
            user_analyses = TextAnalysis.objects.filter(user=request.user)
            
            for analysis in user_analyses:
                if analysis.content:
                    words = word_tokenize(analysis.content.lower())
                    valid_words = [word for word in words if is_valid_word(word)]
                    user_text_words.update(valid_words)
            
            # Tekrar zamanı gelmiş veya geçmiş kelimeleri getir
            due_words = Word.objects.filter(
                user=request.user,
                text__in=user_text_words,
                next_review__lte=now  # next_review şu andan küçük veya eşit olanlar
            ).select_related('dictionary_word')

            # Hiç çalışılmamış kelimeleri getir (en sık geçenler)
            new_frequent_words = Word.objects.filter(
                user=request.user,
                status=0,  # Hiç çalışılmamış
                text__in=user_text_words,
                dictionary_word__isnull=False  # Sadece sözlükte olan kelimeleri al
            ).order_by('-frequency')[:15]  # En sık geçen 15 kelime

            # Hiç çalışılmamış kelimelerden random 5 tane seç (en sık geçen 15 kelime hariç)
            frequent_word_ids = [word.id for word in new_frequent_words]
            new_random_words = Word.objects.filter(
                user=request.user,
                status=0,  # Hiç çalışılmamış
                text__in=user_text_words,
                dictionary_word__isnull=False
            ).exclude(
                id__in=frequent_word_ids
            ).order_by('?')[:5]  # Random 5 kelime

            # Tüm listeleri birleştir
            all_words = list(due_words) + list(new_frequent_words) + list(new_random_words)
            
            # Kelimeleri karıştır
            random.shuffle(all_words)

            # Bugünkü çalışma istatistiklerini al
            today_reviews = ReviewLog.objects.filter(
                user=request.user,
                review_date__date=today,
                word__text__in=user_text_words
            ).select_related('word', 'word__dictionary_word')

            # İstatistikleri hesapla
            stats = {
                'reviewed_count': today_reviews.count(),
                'study_minutes': 0,  # Bu özellik henüz eklenmedi
                'correct_count': today_reviews.filter(difficulty__gte=3).count(),
                'wrong_count': today_reviews.filter(difficulty__lt=3).count(),
                'reviewed_words': [{
                    'text': review.word.text,
                    'translation': review.word.dictionary_word.translation if review.word.dictionary_word else '',
                    'result': review.result,
                    'difficulty': review.difficulty,
                    'review_date': review.review_date.isoformat()
                } for review in today_reviews]
            }

            # Kelimeleri serialize et
            serializer = WordSerializer(all_words, many=True)

            return Response({
                'words': serializer.data,
                'due_count': len(due_words),
                'new_count': len(new_frequent_words) + len(new_random_words),
                'stats': stats
            })

        except Exception as e:
            print(f"Error in due_reviews: {str(e)}")
            return Response(
                {'error': 'Tekrar edilecek kelimeler alınırken bir hata oluştu.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]  # Sadece giriş yapmış kullanıcılar

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response(
                {'error': 'Eski ve yeni şifre gereklidir'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {'error': 'Eski şifre yanlış'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {'error': list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Şifre başarıyla güncellendi'})

    @action(detail=False, methods=['post'])
    def delete_account(self, request):
        user = request.user
        password = request.data.get('password')

        if not password:
            return Response(
                {'error': 'Şifre gereklidir'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(password):
            return Response(
                {'error': 'Şifre yanlış'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.delete()
        return Response({'message': 'Hesap başarıyla silindi'})

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    try:
        print("Gelen veri:", request.data)  # Debug için
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        print(f"Username: {username}, Email: {email}, Password: {'*' * len(password) if password else None}")  # Debug için

        if not username or not email or not password:
            return Response(
                {'error': 'Kullanıcı adı, email ve şifre gereklidir'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Bu kullanıcı adı zaten kullanılıyor'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Bu email adresi zaten kullanılıyor'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(password)
        except ValidationError as e:
            return Response(
                {'error': list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # UserProfile oluştur
        UserProfile.objects.create(user=user)

        return Response({
            'message': 'Kullanıcı başarıyla oluşturuldu',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("Hata:", str(e))  # Debug için
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scrape_words(request):
    try:
        url = "https://diziyleogren.com/blog/ingilizce-dizi-ve-filmlerde-en-sik-kullanilan-5000-kelime"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        
        added_count = 0
        updated_count = 0
        
        for row in rows:
            spans = row.find_all('span')
            if len(spans) >= 2:
                word = spans[0].text.strip().lower()
                translation = spans[1].text.strip()
                
                if is_valid_word(word):
                    # Kelimeyi DictionaryWord tablosuna ekle
                    dictionary_word, created = DictionaryWord.objects.get_or_create(
                        text=word,
                        defaults={'translation': translation}
                    )
                    
                    if not created:
                        dictionary_word.translation = translation
                        dictionary_word.save()
                        updated_count += 1
                    else:
                        added_count += 1
        
        return Response({
            'message': 'Kelimeler başarıyla çekildi',
            'added_count': added_count,
            'updated_count': updated_count
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

class DictionaryWordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = DictionaryWord.objects.all()
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(text__icontains=search)
        return queryset.order_by('text')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DictionaryWordCreateSerializer
        return DictionaryWordSerializer

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        try:
            # Toplam kelime sayısı
            total_words = DictionaryWord.objects.count()
            
            # Çevirisi olan kelimeler (boş string ve null değerleri hariç)
            words_with_translation = DictionaryWord.objects.exclude(
                Q(translation__isnull=True) | Q(translation__exact='')
            ).count()
            
            # Doğrulanmış kelimeler
            verified_words = DictionaryWord.objects.filter(is_verified=True).count()
            
            # En son güncellenen kelime
            last_updated = DictionaryWord.objects.order_by('-updated_at').first()
            
            # Raporlanmış kelimeler
            reported_words = DictionaryWord.objects.filter(report_count__gt=0).count()
            
            return Response({
                'total_words': total_words,
                'words_with_translation': words_with_translation,
                'verified_words': verified_words,
                'reported_words': reported_words,
                'last_updated': last_updated.updated_at if last_updated else None
            })
        except Exception as e:
            print(f"Sözlük istatistikleri alınırken hata: {str(e)}")
            return Response({
                'error': 'İstatistikler alınırken bir hata oluştu'
            }, status=500)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        word = self.get_object()
        reason = request.data.get('reason')
        
        if not reason:
            return Response({'error': 'Lütfen bir neden belirtin'}, status=400)
            
        try:
            report = DictionaryReport.objects.create(
                word=word,
                reported_by=request.user,
                reason=reason
            )
            word.report_count = F('report_count') + 1
            word.save()
            
            return Response({'message': 'Kelime başarıyla raporlandı'})
        except IntegrityError:
            return Response({'error': 'Bu kelimeyi zaten raporlamışsınız'}, status=400)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'error': 'Bu işlem için yetkiniz yok'}, status=403)
            
        word = self.get_object()
        word.is_verified = True
        word.verified_by = request.user
        word.verified_at = timezone.now()
        word.save()
        
        return Response({'message': 'Kelime doğrulandı'})

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        translations = request.data.get('translations', [])
        if not translations:
            return Response({'error': 'Çeviri listesi boş'}, status=400)
            
        added_count = 0
        updated_count = 0
        
        for item in translations:
            text = item.get('text', '').strip().lower()
            translation = item.get('translation', '').strip().lower()
            
            if not text or not translation:
                continue
                
            word, created = DictionaryWord.objects.get_or_create(
                text=text,
                defaults={
                    'translation': translation,
                    'added_by': request.user
                }
            )
            
            if created:
                added_count += 1
            else:
                # Eğer kelime doğrulanmamışsa güncelle
                if not word.is_verified:
                    word.translation = translation
                    word.save()
                    updated_count += 1
        
        return Response({
            'message': 'İşlem tamamlandı',
            'added_count': added_count,
            'updated_count': updated_count
        })
