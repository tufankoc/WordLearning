# Repository Rules (for Cursor)

## Amaç
- Açık kaynak, Django tabanlı bir kelime öğrenme uygulaması.
- Güvenlik, şeffaflık ve sürdürülebilirlik önceliklidir.

## Güvenlik ve Gizli Bilgiler
- Gerçek anahtarlar, token’lar, çerezler commit edilmez.
- `.env` dosyası commit edilmez; `.gitignore` hariç tutar.
- Örnek ortam değişkenleri için `ENV.sample` (veya `.env.example`) kullanılır.
- Ayarlar ortam değişkenlerinden beslenir; sabit gizli değer kullanılmaz.

## Bağımlılıklar
- Gereksiz kütüphane eklemeyin; önce standart kütüphane/mevcut bağımlılıklar.
- Yeni kütüphane gerekiyorsa gerekçe, kapsam ve lisans uyumu belirtin.
- `requirements.txt` sürüm sabitlemesi korunur.

## Django Kuralları
- Üretim ayarları env ile kontrol edilir (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, CORS/CSRF, throttle).
- Statik dosyalar: geliştirmede `static/`, üretimde `STATIC_ROOT=staticfiles/`.
- Veritabanı: geliştirmede `sqlite3`; üretimde env temelli yapılandırma yapılabilir.
- Admin güvenlik middleware’leri korunsun; değişiklikler PR açıklamasında gerekçelendirilsin.

## Kod Stili
- Python 3.12+. Anlamlı isimlendirme, erken dönüşler, kenar durumları önce.
- Yorumlar kısa ve “neden” odaklı.
- Tip ipuçları kamu API’lerinde tercih edilir.

## Test ve CI
- GitHub Actions: `.github/workflows/ci.yml` yeşil kalmalı.
- `manage.py check`, `migrate --noinput`, `test --noinput` kırmızı olmamalı.
- Harici API bağımlı testler flaky ise mock/skip ile stabilize edilir.

## Git ve PR
- Ana dal: `main`.
- Küçük, odaklı PR’lar; amaç, kapsam, etki ve güvenlik notlarıyla.
- README/ENV örneği gereken değişiklikler PR’da güncellenir.

## Betikler
- `test_*.sh` betikleri token’ları ortamdan okur: `TOKEN`, `PRO_TOKEN`, `FREE_TOKEN`.
- Dokümantasyon örneklerinde “YOUR_*_TOKEN” placeholderları kullanılmalı.

## Lisans
- MIT. Üçüncü taraf lisanslara uyum; kopyalanan kodda lisans başlıkları korunur.

## İletişim (Cursor Yardımcısı için)
- Kısa, yüksek sinyalli yanıtlar; gerekirse maddeler halinde.
- Dosya/klasör/fonksiyon adlarını backtick ile biçimlendirin.
- Kod paylaşımlarında yalnızca ilgili kısımlar; açıklamalar metinde.
- Büyük düzenlemeler sonrası test/build çalıştırmayı hatırlatın.
