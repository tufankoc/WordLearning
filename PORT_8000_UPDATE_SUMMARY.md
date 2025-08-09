# Port 8000 Güncelleme Özeti

## ✅ Yapılan Değişiklikler

Tüm dosyalarda port numarası **8004'ten 8000'e** güncellendi:

### 1. Test Scripts
- `test_api_with_curl.sh` - BASE_URL güncellendi
- `test_enhanced_source_api.py` - BASE_URL güncellendi

### 2. Documentation  
- `SOURCE_API_DEBUG_SUMMARY.md` - Tüm port referansları güncellendi

## 🚀 Kullanım

### Server Başlatma
```bash
python manage.py runserver 8000
```

### API Test Etme
```bash
# Bağlantı testi
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/debug/test/"

# Test script çalıştırma
./test_api_with_curl.sh
```

### API Endpoints (Port 8000)

| Endpoint | Method | Açıklama |
|----------|---------|----------|
| `/debug/test/` | GET/POST | Debug endpoint |
| `/sources/enhanced/` | POST | Enhanced source creation |
| `/api/sources/` | GET/POST | Legacy source API |

## 📝 API Usage Examples

### Manual Text (Port 8000)
```bash
curl -X POST "http://localhost:8000/sources/enhanced/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "title": "Test Text",
    "manual_text": "Sample content with vocabulary words."
  }'
```

### Web URL (Port 8000)
```bash
curl -X POST "http://localhost:8000/sources/enhanced/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "title": "News Article",
    "web_url": "https://www.bbc.com/news"
  }'
```

### PDF File (Port 8000)
```bash
curl -X POST "http://localhost:8000/sources/enhanced/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "pdf_file=@document.pdf" \
  -F "title=My PDF Document"
```

### YouTube URL (Port 8000)
```bash
curl -X POST "http://localhost:8000/sources/enhanced/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "title": "Educational Video",
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }'
```

### SRT Subtitles (Port 8000)
```bash
curl -X POST "http://localhost:8000/sources/enhanced/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "srt_file=@subtitles.srt" \
  -F "title=Movie Subtitles"
```

## ✅ Test Results (Port 8000)

- ✅ Server port 8000'de çalışıyor
- ✅ API endpoints erişilebilir 
- ✅ Authentication sistemi çalışıyor
- ✅ Debug endpoint aktif
- ✅ Error handling doğru çalışıyor

## 🎯 Sonuç

Tüm API endpoint'leri ve test araçları başarıyla **port 8000'e** güncellendi. Uygulama artık varsayılan Django portu olan 8000'de çalışacak şekilde yapılandırıldı. 