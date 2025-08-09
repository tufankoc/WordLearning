<<<<<<< HEAD
## ✨ New Features

### 🌟 Modern Landing Page
- **Public-facing homepage** at `/` for anonymous users
- **Automatic redirect** to dashboard for authenticated users
- **Responsive design** with Tailwind CSS
- **Call-to-action buttons** for signup and login
- **Dynamic user statistics** (users, words learned, countries)
- **Social proof** with testimonials and trust signals
- **Share functionality** with Web Share API fallback
- **Open Graph tags** for social media previews

### 📊 Admin Analytics Dashboard
- **Enhanced Django admin** with detailed user statistics
- **Custom analytics dashboard** for superusers
- **User engagement tracking** and business metrics
- **Advanced filtering** and management tools

### 🔒 Enterprise Security
- **Multi-layer admin security** with superuser restrictions
- **Comprehensive logging** for all admin activities
- **Access control middleware** with automatic redirects
- **Permission-based UI** with graceful error handling

## 🚀 Quick Start

1. **Visit the landing page**: Go to `http://localhost:8000/` to see the new public homepage
2. **Sign up for free**: Click "Try it free" to create an account
3. **Login**: Existing users can login and be redirected to their dashboard
4. **Admin access**: Staff users can access `/admin/`, superusers get `/superuser-admin/`

## 📱 User Experience

- **Anonymous users** → See beautiful landing page with product info
- **Authenticated users** → Automatically redirected to dashboard
- **Non-admin users** → Redirected to settings when trying to access admin
- **Mobile responsive** → Works perfectly on all devices

## 🎨 Design Features

- **Modern gradient backgrounds** and smooth animations
- **Professional navigation** with clear call-to-action buttons
- **Three-step process** explanation with icons
- **User testimonials** and social proof elements
- **Interactive share button** for viral growth
- **SEO optimized** with proper meta tags and Open Graph

The landing page showcases Kelime as a modern vocabulary learning SaaS with compelling copy, beautiful design, and seamless user flow from discovery to signup. 

## Getting Started

### Prerequisites
- Python 3.12+
- pip

### Setup
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and set DJANGO_SECRET_KEY, etc.
   ```
4. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

### Running Tests
```bash
python manage.py test --noinput
```

### Security & Secrets
- Do not commit real tokens, API keys, or cookies.
- Local artifacts like `db.sqlite3`, logs, and `.env` are ignored via `.gitignore`.
- `kelime/settings.py` reads configuration from environment variables.

### CI
This repository includes a GitHub Actions workflow at `.github/workflows/ci.yml` that installs dependencies, runs Django checks, applies migrations, and executes tests on pushes and PRs.

### Example Scripts
Shell scripts under the project root (e.g., `test_api_with_curl.sh`) now read tokens from environment variables. Set them before running:
```bash
export TOKEN=YOUR_TOKEN_HERE
export PRO_TOKEN=YOUR_PRO_TOKEN
export FREE_TOKEN=YOUR_FREE_TOKEN
```

### License
MIT — see `LICENSE`.
=======
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
>>>>>>> origin/main
