# Classifieds Local — bağımsız yerel çekirdek

Classifieds Local, Türkçe bir ilan uygulamasının ilk çalışan çekirdeğidir. Yeni uygulama `rebuild/` altında Django Templates, HTMX, PostgreSQL, Celery ve Redis kullanır. Satıcı taslağı, özel fotoğraflar, zorunlu e-posta doğrulaması, izinli inceleme ve yalnız onaylı sürümün yayımlanması çalışır.

Son bağımsız inceleme tamamlandı; belirlenen dokuz küçük bulgu giderildi. Phase 1'de yeni uygulamanın 155 testlik tam paketi geçti. Bu sürüm yerel geliştirme kapsamındadır; ayrıntılı sonuçlar [VERIFICATION.md](docs/VERIFICATION.md) ve [son bağımsız inceleme raporunda](docs/implementation/final-fix-review.md) kayıtlıdır. Bu sonuç tüm ürünün, eski repository'nin veya bir Git checkpoint'inin tamamlandığı anlamına gelmez.

## Aktif uygulama ve geliştirme ortamı

2026-10-09 yerel benimsemesinden sonra iki bağımsız runtime vardır:

| Amaç | Repository kökü | Compose projesi | Tarayıcı adresi | Uygulama image etiketi |
| --- | --- | --- | --- | --- |
| Aktif yerel uygulama | `C:\Users\ismai\Desktop\classifieds_local` | `classifieds-rebuild` | [http://127.0.0.1:8088/](http://127.0.0.1:8088/) | `classifieds-rebuild-web:local` |
| Sonraki geliştirmeler | `C:\Users\ismai\.devspace\worktrees\classifieds_local-a7be577c` | `classifieds-rebuild-dev` | [http://localhost:8089/](http://localhost:8089/) | `classifieds-rebuild-dev-web:local` |

Aktif web, worker ve scheduler artık asıl repository'nin `rebuild/backend` kaynağına salt okunur `/app` bind ile bağlıdır. 2026-10-09 benimsemesinde kabul edilen image ID'si `sha256:112f9056e01531e86428baca5ec861f8c2c53a89c4a3e0173859b6a6d41701e7` idi. Bu değer Phase 1 benimsemesinin tarihsel kaydıdır; sonraki arama sürümünün aktif kabul durumu [search-release-report.md](docs/phase2/search-release-report.md) içinde kayıtlanır. DB/Redis container'ları yeniden oluşturulmadı; şu beş volume değişmedi: `classifieds-rebuild_rebuild_postgres`, `classifieds-rebuild_rebuild_redis`, `classifieds-rebuild_rebuild_media`, `classifieds-rebuild_rebuild_static`, `classifieds-rebuild_rebuild_scheduler`. Aynı kodun yol değişimi için aktif DB'ye migration veya seed uygulanmadı. Eski uygulama verisi taşınmadı.

Geliştirme komutlarını yalnız worktree kökünde, her seferinde **iki Compose dosyası ve geliştirme proje adıyla** çalıştırın. `compose.dev.yaml`, web port listesini `!override` ile yalnız `127.0.0.1:8089:8000` yapar. Compose v5.3.1 üzerinde birleşmiş config doğrulandı. Kaynak worktree'den salt okunur bağlanır; beş volume `classifieds-rebuild-dev_` önekiyle ayrıdır. PostgreSQL ve Redis iki ortamda da host portu açmaz. Geliştirme tarayıcısında `localhost:8089` kullanılması, aktif `127.0.0.1:8088` hostunun oturum cookie'lerini ayırır.

Docker Engine ve Docker Compose gerekir. Host Python kurulumu gerekmez; Django komutları ilgili yeni `web` container'ında çalışır. Kilitli ortam Python 3.12.15 / Linux amd64, Django 5.2.18, django-allauth 65.19.7, PostgreSQL 17.11 ve Redis sunucusu 7.4.11'dir. Python wheel sürüm/hash'leri `requirements.lock` içindedir; kurulum `--require-hashes --only-binary=:all:` kullanır.

## İzole geliştirme ilk kurulumu

Aşağıdaki sıra yeni geliştirme DB'si içindir; mevcut aktif DB'yi yeniden hazırlama komutu değildir:

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev build web
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev up -d --no-build --wait --wait-timeout 120 db redis
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev up -d --no-build --wait --wait-timeout 120 web
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py migrate --noinput
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py setup_local --domain localhost:8089
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev up -d --no-build --wait --wait-timeout 120 worker scheduler
```

`setup_local`, yerel Site adını/alan adını ayarlar ve geliştirme kategorilerini oluşturur; mevcut şema sürümlerini korur, kullanıcı/parola/doğrulama/oturum verisini değiştirmez. Yalnız DEBUG ve yerel alan adı kabul eder. Worker/scheduler migration sonrasında başlatılır. Bu benimseme paketinde hesap veya credential oluşturulmadı.

Aktif uygulama normal başlangıcı asıl repository kökünden:

```bash
docker compose -f rebuild/compose.yaml -p classifieds-rebuild up -d --no-build db redis web worker scheduler
```

Bu komut mevcut kabul edilmiş image ve volume'ları kullanır. İki ortamın özel `REBUILD_*` ortam değerleri yalnız operatörün yerel ortamında yönetilir; private env dosyaları bu geçişte kopyalanmadı veya değiştirilmedi. Geçiş öncesi her uygulama servisinin dokuz Compose ortam anahtarı ve DB'nin üç anahtarı mevcut runtime ile bellek içinde eşit bulundu. DB kimlik değişikliği mevcut volume üzerinde ilk kurulum yerine geçmez.

`/health/` DB bağlantısını denetler. DEBUG statik route'u yerel Gunicorn altında CSS/HTMX sunar; bu kabul yalnız yereldir. Güncel benimseme/test/izolasyon kanıtı [adoption-report.md](docs/phase2/adoption-report.md) içindedir; eski [VERIFICATION.md](docs/VERIFICATION.md) Phase 1 tarihsel kaydıdır.

## Satıcı ve inceleyici hesapları

1. `/accounts/signup/` üzerinden kendi seçtiğiniz e-posta ve parola ile satıcı hesabı açın. E-posta doğrulaması zorunludur. Yerel console e-posta backend'i dışarı posta göndermez; doğrulama bağlantısını yalnız kendi yerel web çıktınızdan açın. Parola, e-posta tokenı veya bağlantısını paylaşmayın.
2. `/accounts/login/` üzerinden giriş yapın. `/ilan-ver/` ile kategori seçip gerçek bir taslak oluşturun. Fotoğraflar → detaylar → özel önizleme/gönder adımlarını izleyin. Fotoğraflar isteğe bağlıdır; eklenen fotoğrafların işlenmiş olması gerekir.
3. İnceleyici için ayrı bir hesap açın ve o hesabın e-postasını doğrulayın. Yerel yönetici gerekiyorsa aşağıdaki etkileşimli komutu kullanın; parola komut argümanına yazılmaz:

```bash
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec web python manage.py createsuperuser
```

4. Yönetici `/admin/` içindeki Users ekranında seçilen inceleyici hesabının User permissions alanına **`listings.review_listingrevision`** iznini versin. İnceleyici hesabı için superuser veya staff gerekmez. Staff işareti tek başına inceleme yetkisi vermez.
5. İnceleyici `/inceleme/` üzerinden gönderilmiş sürümü açıp zorunlu gerekçe ile onaylar veya reddeder. Ret gerekçesi sahibinin özel ekranında görünür. Onaydan önce ziyaretçi taslak içeriği veya fotoğrafını göremez.

`browser_fixture` sentetik tarayıcı test yardımcısıdır; normal hesap kurulumu yerine kullanılmaz. Zorunlu doğrulama, session auth ve CSRF açık kalır.

## Günlük kullanım ve sürüm davranışı

| Ekran | Gerçek route |
| --- | --- |
| Herkese açık ilan listesi | `/` |
| Güncel onaylı ilan | `/ilanlar/<listing_uuid>/` |
| Sahibinin ilanları | `/ilanlarim/` |
| Yeni kategori/taslak | `/ilan-ver/` |
| Taslak fotoğrafları | `/taslaklar/<revision_id>/duzenle/` |
| Taslak detayları | `/taslaklar/<revision_id>/duzenle/?step=details` |
| Özel önizleme | `/taslaklar/<revision_id>/onizleme/` |
| İnceleme kuyruğu | `/inceleme/` |
| Tek sürüm inceleme | `/inceleme/<revision_id>/` |

İlan ve sürüm ID'lerini gerçek uygulama bağlantılarından alın. Taslak kaydetme, gönderme, geri çekme, yeniden düzenleme ve fotoğraf işlemleri POST/CSRF üzerinden çalışır. Gönderilmiş içerik değişmezdir; yeni düzenleme ayrı taslak oluşturur. İlanlarım ekranı mevcut yayını ve bekleyen değişikliği ayrı gösterir. Yeni sürüm onaylanana kadar ziyaretçiler önceki onaylı sürümü görür.

Güncel public pointer, yaşam döngüsü, sona erme ve aktif kısıtlamalar liste/detay/fotoğraf için ortak görünürlük kuralıdır. Fotoğraf ayrıca tam ilan/sürüm/asset ilişkisini doğrular. Orijinal fotoğraflar özeldir. Owner public URL'de de yalnız güncel onaylı içeriği görür; özel önizleme ayrı route'tur. Özel önizleme sayfasının erişim sınırı, onaylı sürümün herkese açık ilan sayfasındaki görünürlüğünü değiştirmez. Geçersiz veya aşırı uzun kategori filtresi tüm kategoriler görünümüne döner.

## Aktif benimseme doğrulaması ve geliştirme testleri

Asıl repository kökünden aktif uygulama doğrulaması:

```bash
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python -m pip check
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py check
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py makemigrations --check --dry-run
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py migrate --check
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py test catalog listings media moderation --verbosity 1
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py test --verbosity 1
docker compose -f rebuild/compose.yaml -p classifieds-rebuild ps
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web celery -A config inspect ping --timeout 5
curl --fail --silent --show-error http://127.0.0.1:8088/health/
git diff --check
```

2026-10-09 benimsemesinde asıl kaynak üzerinde `check` ve migration dry-run geçti; tam NEW paket **155 test / 81.042s** PASS verdi. İzole geliştirme sağlık/worker kontrolleri geçti; aynı 155 test burada yeniden çalıştırılmadı. Ayrıntılar [benimseme raporunda](docs/phase2/adoption-report.md).

Sonraki değişikliklerin testlerini worktree'de çalıştırın:

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py check
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py makemigrations --check --dry-run
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test --verbosity 1
```

**Tarihsel Phase 1 kanıtı:** Tek final dalga gerçekten **53 focused / 21.791s** ve **155 full NEW / 84.969s** PASS verdi; altı yeni generator/transparency/category/copy regression'ı önce beklenen RED ile doğrulandı. Güncel image rebuild ve normal Celery worker smoke/replay de geçti. Task6'nın önceki 137 hedef / 149 full sonucu tarihsel kanıttır; final dalgada hedef suite tekrar çalıştırılmadı.

Test runner yalnız yeni proje DB'sinde geçici test veritabanı oluşturur ve normal şekilde kaldırır. Kaynak, migration ve model üretimi host üzerinden yapılmaz. `git diff --check` untracked dosyaları kapsamaz; final kaynak denetimi bunları ayrıca kontrol eder.

Tarihsel tarayıcı doğrulaması ve gizlilik sınırları [LOCAL_SETUP.md](docs/LOCAL_SETUP.md) ile Task5 raporunda açıklanır. Önceki gerçek tarayıcı kanıtı 144 journey ve 20 örneklenmiş sunum assertion'ıdır; Task6 ve tek final düzeltme dalgası bu tarayıcı akışını tekrar çalıştırmadı. Final category/preview/details değişiklikleri gerçek rendered HTTP regression'larıyla denetlendi; önceki screenshot'lar korunur.

`.github/workflows/rebuild-ci.yml` yalnız yeni Compose projesini GitHub-hosted Ubuntu runner'da oluşturup doğrular. Check-out tam SHA ile kilitli, izinler contents:read ve dağıtım yoktur. Workflow, backend ve açık packaging/runtime/browser/onboarding yollarından oluşan güncel kaynak manifest'inin tam içeriğini diagnostic-aware no-index whitespace gate ile denetler; yeni commit'teki hata temiz checkout'ta da yakalanır. Yerelde clean fixture kabulü ve trailing-space/EOF fixture reddi doğrulandı; implementation raporları/snapshot'ları bu kaynak gate'ine dahil değildir. Workflow dosyasının yazılması uzaktaki CI'nin geçtiği anlamına gelmez; remote CI **NOT RUN**. Son resource cleanup yalnız workflow içindeki korumalı geçici GitHub-hosted runner adımıdır; yerel kullanım komutu değildir.

## Kapsam ve sonraki paketler

Bu dilim hesap/kategori, taslak revizyonu, özel medya işleme, izinli inceleme, onaylı public görünürlük ve yerel UI içerir. Ödeme, reklam, mesajlaşma, açık artırma, eski veri migration'ı, harici e-posta teslimi veya canlı dağıtım içermez. Outbox kayıtları kalıcıdır; harici teslimat consumer'ı henüz yoktur.

Arama/filtre paketi ayrı geliştirme ortamında uygulanmıştır. SearchSpec v1, Türkçe GET araması, kategori/özellik filtreleri ve kararlı sayfalama için güncel kabul kanıtı [SEARCH_VERIFICATION.md](docs/SEARCH_VERIFICATION.md) içindedir. Aktif ortama aktarım ve image/migration doğrulaması ayrı [search-release-report.md](docs/phase2/search-release-report.md) kaydında izlenir.

Sonraki ayrı kapsamlar pilot hesap güvenliği (MFA, abuse/rate/quota ve operatör yetkileri), işletim (yedek/restore, kurtarma, worker/scheduler/outbox gözlemi ve private medya orphan uzlaştırması), profil/iletişim ve domain paketleri, ardından ayrı canlı dağıtım hazırlığıdır.

Mevcut upload view non-atomic çalışır ve attachment service kendi transaction sınırını yönetir. Gelecekte bu service'i outer transaction içine alan caller, rollback sonrası özel original dosya compensation/reconciliation işini ayrıca tasarlamalıdır; genel orphan subsystem bu dilimde yoktur.

Dokuz Minor disposition'ı, kabul edilen bu gelecekteki sınır ve test/inceleme sınırları [VERIFICATION.md](docs/VERIFICATION.md) içinde açıkça listelenir.

## İlanlarda arama

Ana sayfadaki “İlanlarda ara” formu anahtar kelime, kategori, alt kategoriler, konum, para birimi ve fiyat aralığıyla çalışır. En yeni, aynı para biriminde artan/azalan fiyat veya anahtar kelimeyle ilgililik sıralaması seçilebilir. TRY/EUR/USD öneridir; CHF gibi diğer üç ASCII harfli para birimi kodları da kabul edilir. Fiyatlar için nokta ayracı kullanın: `1000.50`. Para birimleri birbirine çevrilmez.

Kategori seçtikten sonra **Kategoriyi uygula** düğmesine basın. Bu işlem ortak ölçütleri korur, önceki kategori özelliklerini temizler ve seçilen kategorinin alanlarını getirir. **Ara**, girilen ölçütlerle yeni aramayı başlatır ve sayfayı sıfırlar. Kategori değiştirip eski özelliklerle doğrudan aramak görünür hata verir. **Filtreleri temizle** tüm ilanlar görünümüne döner. Bu akış JavaScript kapalıyken de normal GET formu ve bağlantılarla çalışır.

Kategoriye özel sayısal alanlar alt/üst sınır, seçenek alanları tam eşleşme, booleans Tümü/Evet/Hayır olarak sunulur. Metin özellikleri tam eşleşir. Alt kategoriler dahil aramada farklı kategorilerin özellikleri tahmin edilmez; ortak ölçütler kullanılır. Canonical sayfa bağlantıları seçili kaynak ve uyumlu kategori şemalarını korur. Her sayfada en fazla12 ilan gösterilir; eşit tarih/fiyatlarda UUID son bağlayıcısı sıralamayı kararlı tutar. Eşzamanlı yayımlar arasında sonuçlar bir snapshot değildir.

Geçersiz yeni ölçütlerde bağlı alan hataları gösterilir ve ilan sorgusu çalıştırılmaz. Bu durum başarılı fakat sonuçsuz aramadan ayrıdır. Önceki kategoriye ait geçersiz değerler hata ekranında korunur. Eski kategori parametresinin biçimi geçersizse önceki tüm kategoriler davranışı sürer; geçerli fakat bulunmayan pozitif kategori ID'si sonuç üretmez.

Metin araması Türkçe büyük/küçük harf ve belirtilen aksanları ortaklaştırır, çoklu kelimeleri birlikte arar; yazım hatası düzeltme veya Türkçe kök bulma iddiası yoktur. Ayrıntılı geliştirici komutları, test sayıları ve gerçek390/1440px tarayıcı kanıtı [SEARCH_VERIFICATION.md](docs/SEARCH_VERIFICATION.md) içindedir.

## Görüşmeler — geliştirme kabulü

Geliştirme uygulamasında Mesajlar menüsü, ilan sahibine ilk mesaj, iki kanonik tarafın yanıt/geçmişi, açık okundu işlemi, kişisel arşiv ve yönlü engelleme çalışır. İlan sahibi yeni görüşmeleri açıp kapatabilir. Mevcut yazışma ilan kapandıktan sonra da devam eder; hesap/engel/mesajlaşma kısıtı gönderimi durdurabilir. E-posta, bildirim, ek dosya veya gerçek hesaplara otomatik mesaj gönderimi bu modülde yoktur.

Gelen kutusu12, mesaj geçmişi30 SQL satırıyla sayfalanır. Türkçe rol etiketleri ve kaçışlı düz metin gösterilir; hesap e-postası gösterilmez. En yeni geçmiş15s HTMX yenilemesini destekler; normal GET yenileme ve POST/CSRF bütün işlemler JavaScript kapalıyken de çalışır. Mesaj sınırı4000 Python Unicode karakteridir; tarayıcının UTF-16 maxlength sınırlaması kullanılmaz.

Gerçek geliştirici Chromium yolculuğu ve PostgreSQL/HTTP doğrulaması [CONVERSATIONS_VERIFICATION.md](docs/CONVERSATIONS_VERIFICATION.md) içinde kayıtlıdır. Asıl uygulamaya aktarım ve bağımsız bütünleşik onay bu geliştirici kabulünden ayrı kök adımlardır.

## Pilot etkinlik sınırları — geliştirici paketi

Başarılı yeni kayıtlar hesap başına kayan pencerede sayılır. Başlangıç değerleri operatörün seçtiği pilot değerleridir; genel DDoS koruması veya üretim hazırlığı iddiası değildir.

| İşlem | Django / ortam ayarı | Varsayılan | Sayılan birim |
| --- | --- | --- | --- |
| Yeni görüşme | `PILOT_NEW_CONTACTS_PER_HOUR` | 10 / 3600 saniye | Başlatanın yeni kanonik `(ilan, başlatan)` Conversation satırı |
| Mesaj | `PILOT_MESSAGES_PER_HOUR` | 120 / 3600 saniye | Gönderenin tüm görüşmelerdeki başarılı Message satırı |
| Yeni ilan kimliği | `PILOT_NEW_LISTINGS_PER_DAY` | 10 / 86400 saniye | Sahibin tüm yaşam döngülerindeki Listing satırı |

Aynı satıcıya ait farklı ilanlar farklı yeni görüşmelerdir. İlk başarılı görüşme hem bir görüşme hem bir mesaj tüketir. Mevcut görüşmenin başlangıç adresinden yanıt yalnız mesaj tüketir. Aynı mesajın geçerli gönderim kimliğiyle aynı içerikte tekrarı yeni kayıt veya kota tüketmez. Yeni ilan oluşturmanın idempotency kimliği yoktur. Yalnız kategoriyle açılan taslak hemen yeni ilan kimliği sayılır. Mevcut taslağı düzenleme, yeni revizyon, gönderme, geri çekme, yayımlama ve görünürlük değişiklikleri yeni Listing oluşturmadığından bu sınırı tüketmez.

Kesim noktası işlemde hesap kilidi alındıktan sonra örneklenen zamandır. `created_at > şimdi - pencere` sayılır; tam bir pencere yaşındaki kayıt artık sayılmaz. Saat geriye giderse gelecekte görünen satırlar ihtiyatlı biçimde sayılmaya devam eder. En yeni en fazla kapasite kadar tarih okunur; sınır küçültülürken büyük geçmişin tüm satırlarını saymak gerekmez. Eşzamanlı işlemler hesap kilidiyle sıralanır. Başarısız/geri alınan işlemler kayıt bırakmaz.

Üç ayar da **1..10000 dahil tamsayı** olmalıdır; sıfır korumayı kapatmaz. Geçersiz değerler adı belirtilen `accounts.E001` sistem denetiminde ve çalışma anında `ImproperlyConfigured` ile reddedilir. Compose ortak app ortamı değerleri web, worker ve scheduler'a iletir. İsteğe bağlı ortam ayarını operatör yönetir; private env dosyaları bu paket tarafından değiştirilmez. Staff/superuser muafiyeti yoktur.

Sınır dolduğunda normal CSRF/HTML POST aynı bağlı formu **HTTP 429** ile gösterir. `Retry-After` pozitif tamsayı saniyedir: en yeni kapasite dilimindeki en eski kaydın penceresi bitene kadar yukarı yuvarlanan bekleme süresidir, en az 1 saniye. Türkçe işlem mesajı beklemeyi açıklar; mesaj içeriği kaçışlı olarak ve gönderim kimliği değişmeden, kategori seçimi korunarak kalır. Özel yanıtlar `Cache-Control: private, no-store` ve `X-Content-Type-Options: nosniff` taşır. Daha sonra form yeniden gönderilebilir; bu başlık otomatik yeniden gönderme veya kapasite rezervasyonu değildir. Başka başarılı işlemler bekleme süresini etkileyebilir.

Geçmiş/gelen kutusu okuma, açık okundu, arşiv/engelleme işlemleri ve mevcut taslaklar kullanılabilir. Normal POST/redirect ve JavaScript kapalı akışlar korunur. Yetki, katılımcı gizliliği ve mevcut doğrulama hataları kotadan önce kendi sözleşmelerini korur.

Koruma yalnız olağan uygulama mutation servislerinin sınırındadır. Ayrı sayaç veya timestamp trigger yoktur; doğrudan ayrıcalıklı ORM/bakım yazımları bu koruma dışındadır. Kimlik doğrulama/MFA, raporlama/itiraz, işletim gözlemi, yedek/restore/kurtarma ve üretim dağıtım hazırlığı ayrıca tamamlanmalıdır.

Geliştirici kabulü yalnız sabit `localhost:8089`, ayrık Compose root/bind, DB/Redis/volume, DEBUG ve developer Site doğrulamasından sonra taze ayrılmış sentetik hesaplar kullanır. Geçmiş olağan servislerle oluşturulur; yalnız satıcının 12 sentetik ilanı için fixture kapsamlı geçici ayar kullanılır ve HTTP öncesi geri yüklenir. Eski büyük arama/gelen-kutusu fixture'larının 25/13 kaydı yalnız kendi korumalı hazırlık kapsamlarında override edilir. Canlı uygulama varsayılanları değişmez.

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test accounts.tests.test_pilot_browser_fixture --verbosity 2 --noinput
node rebuild/browser-tests/pilot-limits.cjs
```

Yeni Chromium runner gerçek masaüstü, 390px mobil ve JavaScript kapalı pointer/klavye/form akışlarını ayrı kaydeder. Replay/ek HTTP kontrolleri varsa gerçek UI sayısına katılmaz; ayrı özet alanında gösterilir. Sentetik credentials, session/CSRF/client token'ları yalnız bellekte tutulur. Özet ve screenshot'lar `rebuild/test-artifacts/pilot-limits/<run>/` içindedir; tam sonuçlar [task-B-report.md](docs/phase4/task-B-report.md) içinde kayıtlanır. Asıl8088 benimsemesi ve tek final tüm-app paketi controller'ın ayrı adımlarıdır.

## Personel iki adımlı doğrulaması — geliştirici paketi

Bildirim/itiraz geliştirme paketi: kullanıcı menüsündeki **Bildirimlerim** ve **Kararlarım**, ayrı yetkili inceleme kuyrukları ve gerçek MFA sınırı. Yeni `review_reports` / `review_appeals` rolleri de MFA gerektirir; itirazı ilk kararı veren kişi sonuçlandıramaz.20/10 günlük yeni-kayıt sınırları, dosyaya bağlı kanıt erişimi ve developer-only tarayıcı doğrulaması [REPORTS_APPEALS_VERIFICATION.md](docs/REPORTS_APPEALS_VERIFICATION.md) içinde açıklanır. Gerçek kabul durumu [Phase6 raporundan](docs/phase6/cli-implementation-report.md) izlenir.

Güvenlik menüsü `/accounts/security/` adresindedir. Staff, superuser ve doğrudan/grup üzerinden `listings.review_listingrevision` izni bulunan aktif hesaplar güncel e-postayı doğrulamadan, bir TOTP cihazını eşleştirmeden ve bu oturumda faktör doğrulamadan özel hesap işlemlerine giremez. Staff işareti inceleme izni vermez. Normal satıcı için eşleştirme isteğe bağlıdır; eşleştiren herkes sonraki girişte iki adımlı doğrulama kullanır. Yönetici girişindeki GET ve POST istekleri allauth girişine gider.

Eşleştirme sonrası on adet sekiz haneli kurtarma kodu yalnız bir kez gösterilir; sonradan indirme yoktur. Kodları çevrimdışı saklayın. Her kod tek kullanımlıktır; yenileme önceki kodları geçersiz kılar. Yönetim oturumunda faktör kanıtı sekiz saat, cihaz kaldırma/kod görüntüleme/yenileme için beş dakika geçerlidir. Cihaz değişimi son doğrulamayla eski cihazı kaldırmayı ve hemen yeni cihaz eşleştirmeyi gerektirir. Bu arada zorunlu hesap işlemleri durur. Cihaz ve bütün kodlar kayıpsa otomatik atlama veya acil parola yoktur; operatör kimlik kurtarma süreci ayrı tasarım gerektirir.

Eksik doğrulamayla gönderilen POST hiçbir işleme girmez ve private403 döner; gövde saklanmaz veya otomatik yinelenmez. Stock allauth yeniden doğrulama istisnası da özel middleware tarafından karşılanır; eski `account_reauthentication_state` MFA akışında kullanılmaz. Güvenli GET aynı origin içinde dönüş yolu taşır. E-posta doğrulama yardımcısı yalnız güncel adresi hedefler ve allauth65.19.7'nin sürüme bağlı `send_verification_email_to_address` entegrasyonuyla normal `confirm_email` ve `manage_email` sınırlarını korur.

TOTP secret ve kurtarma seed'i Fernet ile sürümlü, kimliği doğrulanmış ciphertext olarak saklanır. Ayrı anahtar mevcut Django SECRET_KEY'den HKDF-SHA256/info `classifieds/mfa-at-rest/v1` ile türetilir. Yeni yazılar current key; okuma current ve Django SECRET_KEY_FALLBACKS kullanır. Anahtar döndürmeden önce eski anahtarı güvenli fallback ayarına alın; plaintext veya bilinmeyen sürüm kabul edilmez. Kaynak/report/loglara anahtar veya seed yazmayın.

Hesap güvenliği Redis'in mevcut environment hizmetinde DB1 ve `classifieds-auth` prefix'ini kullanır; Celery DB0'da kalır. Cache.add, tüm Gunicorn worker'larında TOTP kod tekrarını tek kullanıma indirir. Beklenen Redis bağlantı/zaman aşımı private503 verir; süreç-içi cache'e sessiz dönüş yoktur. Bu, hesap güvenliğinin kullanılabilirlik sınırıdır; genel DDoS koruması iddiası değildir. TOTP30s/6 hane/tolerans0 ve allauth normal rate limitleri açıktır.

Normal test runner process-local cache ve sentetik locmem e-posta kullanır; runtime güvenlik anahtarlarını temizlemez. Ayrı concurrency testleri gerçek PostgreSQL/Redis üzerinde benzersiz test prefix'i ve yalnız kendilerine ait tam anahtar silme kullanır. FLUSHDB/shared cache.clear yoktur. Tam paket paralel iki süreçle çalışır:

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test accounts.tests.test_mfa accounts.tests.test_mfa_concurrency --verbosity 2 --noinput
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test --verbosity 1 --parallel 2 --noinput
```

SecurityEvent yalnız actor ID, action, method ve zamanı tutar. Admin ekleme/değiştirme/silme kapalıdır; raw Authenticator admin kaldırıldı. Allauth bazı başarı sinyallerini commit sonrasında verir: bu audit dağıtık veya ürün işlemiyle transaction-atomic teslim garantisi değildir. İlk uygulama geçmişi `docs/phase5/task-A-report.md`, sonraki doğrulama `docs/phase5/task-A-resume-review.md` içindedir.

Gerçek geliştirici tarayıcı kabulü tamamlandı: masaüstü, 390px mobil ve JavaScript kapalı kullanımda **1503 kontrol, 99 gerçek HTML POST, 12 ayrı ek HTTP kontrolü ve 9 güvenli ekran görüntüsü**; son koşu `c28831a0c098bfe4`, gerçek çıkış0. Ayrıntılı kullanım, kurtarma/anahtar yedekleme sınırları ve kesin kabul kapsamı [MFA_VERIFICATION.md](docs/MFA_VERIFICATION.md) içindedir. Bu sonuç asıl8088 aktarımı veya bağımsız son inceleme yerine geçmez.

Güvenlik sayfaları `private, no-store` ve `nosniff` yanında `Referrer-Policy: same-origin` kullanır: başka sitelere referrer gönderilmez, gerçek form POST'larında aynı-origin CSRF kanıtı korunur. `no-referrer` gerçek tarayıcıda `Origin:null` ürettiğinden bu akışta kullanılmaz. CSRF kontrolleri veya güvenilen origin listesi gevşetilmemiştir.

Yalnız izole worktree kökünde tarayıcı kabulünü tekrarlama:

```bash
node --test --test-reporter=spec rebuild/browser-tests/mfa.test.cjs
node rebuild/browser-tests/mfa.cjs
```

Her koşu yalnız yeni ayrılmış sentetik geliştirici hesapları kullanır; gerçek hesapların MFA cihazını/parolasını değiştirmez. Önceki sentetik veriler silinmez; test inceleme kuyruğunda olağan sayfalama bağlantılarını izler. Asıl uygulamaya aktarım son bütünleşik inceleme, image/kaynak doğrulaması ve koruma/geri dönüş kontrollerinden sonra ayrı yapılır.
