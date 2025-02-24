# WordLearning - Kelime Öğrenme ve Aralıklı Tekrar Sistemi

Bu proje, kullanıcıların İngilizce metinler üzerinden kelime öğrenmesini ve öğrenilen kelimeleri aralıklı tekrar yöntemiyle pekiştirmesini sağlayan bir web uygulamasıdır.

## Özellikler

- **Metin Analizi**: PDF veya metin olarak yüklenen dokümanlardan kelime çıkarımı ve analizi
- **Aralıklı Tekrar**: Bilimsel aralıklı tekrar algoritması ile kelime öğrenme
- **İlerleme Takibi**: Detaylı istatistikler ve grafiklerle öğrenme sürecini takip
- **Sözlük Entegrasyonu**: Otomatik çeviri ve telaffuz desteği
- **Kategori Yönetimi**: Metinleri kategorilere ayırarak organize etme
- **Çoklu Dil Desteği**: Türkçe arayüz
- **Responsive Tasarım**: Mobil uyumlu arayüz

## Teknolojiler

### Backend
- Django
- Django REST Framework
- PostgreSQL
- NLTK (Natural Language Processing)
- JWT Authentication

### Frontend
- React
- TypeScript
- Tailwind CSS
- Axios
- React Router
- React Context API

## Kurulum

### Backend Kurulumu

1. Python 3.8+ yüklü olmalıdır
2. Virtual environment oluşturun ve aktif edin:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

4. Veritabanı migrasyonlarını yapın:
```bash
python manage.py migrate
```

5. Sunucuyu başlatın:
```bash
python manage.py runserver
```

### Frontend Kurulumu

1. Node.js 14+ yüklü olmalıdır
2. Frontend dizinine gidin:
```bash
cd frontend
```

3. Bağımlılıkları yükleyin:
```bash
npm install
```

4. Geliştirme sunucusunu başlatın:
```bash
npm start
```

## Kullanım

1. Kayıt olun veya giriş yapın
2. "Metin Yükle" sayfasından PDF veya metin yükleyin
3. Analiz sonuçlarını inceleyin
4. "Pratik" sayfasından kelime çalışın
5. İlerlemenizi "İstatistikler" sayfasından takip edin

## Katkıda Bulunma

1. Bu repository'yi fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## İletişim

Tufan Koç - [@tufankoc](https://github.com/tufankoc)

Proje Linki: [https://github.com/tufankoc/WordLearning](https://github.com/tufankoc/WordLearning) 