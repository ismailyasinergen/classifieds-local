# Bağımsız ilan platformu — ürün ve mimari şartnamesi

## Hedef ve varsayımlar

Küçük bir ekibin işleteceği, mobil web öncelikli, çok kategorili bir ilan platformu. Kullanıcı ilan oluşturur, başka kullanıcıların ilanlarını bulur ve platform içinde iletişim kurar. Aynı hesap hem ilan verebilir hem ilanlara mesaj gönderebilir. Gelişmiş işletme vitrini isteğe bağlıdır.

Ana başarı ölçümü, yayımlanan ilanların satıcının yanıtladığı görüşmelere dönüşmesidir. Arama sonuçsuzluk oranı, ilan oluşturmayı terk etme ve moderasyon bekleme süresi de izlenir. Büyük trafik sayıları veya önceki projelerin işlem akışları varsayılmaz.

## Global Constraints

- Uygulama: Django 5.2 LTS serisi; kurulumda güncel güvenlik yaması resmî kaynaktan doğrulanıp kilitlenir.
- Veritabanı: PostgreSQL 17; geliştirme veritabanı mevcut projeden ayrıdır.
- Python: 3.12; bağımlılıkların kesin sürümleri ilk kurulumda doğrulanıp lock dosyasına yazılır.
- Ön yüz: Django Templates + HTMX; mobil uyumlu ve klavye ile kullanılabilir.
- İş yürütme: Celery + Redis; önemli iş ve teslimat kayıtlarının kalıcı kaynağı PostgreSQL'dir.
- Kimlik: özel Django User modeli ve django-allauth; hesap e-postası public iletişim bilgisinden ayrıdır.
- İlk uygulama yalnız yerel geliştirme ürünüdür; canlı dağıtım veya eski veriye migration kapsam dışıdır.
- Yeni uygulama `rebuild/` altında bağımsızdır; eski backend modüllerini import etmez.
- Compose proje adı `classifieds-rebuild`; Django servis adı `web`; geliştirme HTTP adresi varsayılan olarak `127.0.0.1:8088` üzerinden bağlanır.
- Aynı repository içindeki kök AGENTS talimatları geçerlidir. Commit/tag/push/merge/dağıtım bu pakette yapılmaz.
- Django komutları ilgili `web` container'ında çalışır. Yeni çekirdek ve eski repository doğrulama sonuçları ayrı raporlanır.

Bu sürüm seçimleri tasarım kararlarıdır; bu hazırlıkta kurulmuş veya çalıştırılmış bağımlılıklar değildir.

## Modül sınırları

| Modül | Sahip olduğu kavramlar |
| --- | --- |
| accounts | User, public profil, doğrulama, oturum ve iletişim tercihleri |
| catalog | Kategori ağacı ve sürümlü kategori özellik şemaları |
| listings | Listing, ListingRevision, yayımlama, süre ve yayımlanmış fiyat geçmişi |
| conversations | Görüşme, mesaj, katılımcı okuma durumu, engelleme |
| moderation | İnceleme dosyası, karar, kısıtlama, itiraz |
| notifications | Kayıtlı arama, bildirim tercihi, olay eşleştirme ve teslimat |
| promotions | Ürün, satın alma koşulları ve etkinleştirme |
| media | Dosya sahipliği, orijinal/türev, işleme durumu ve erişim |
| events | Küçük kalıcı outbox ve olay tüketim kayıtları |

Yetki ve durum geçişleri açık hizmet fonksiyonlarında yönetilir. Web, admin ve görevler aynı hizmetleri çağırır. Okuma sorguları ilgili modülde tutulur. Modellerin save metotlarına veya sinyallere çok adımlı yayımlama/ödeme akışları gizlenmez.

## Listing ve ListingRevision

Listing kalıcı UUID, owner, lifecycle, public_revision, first_published_at ve expires_at tutar. Lifecycle değerleri `draft`, `live`, `paused`, `closed` olur. Süre dolması zaman koşulundan türetilir.

ListingRevision ilanın başlık, açıklama, fiyat/para birimi, kategori, konum, özellik ve fotoğraf içeriğini tutar. Durumlar `draft`, `submitted`, `approved`, `rejected`, `withdrawn` olur. Sonuncusu, gönderilmiş içeriğin sabitliğini koruyarak kullanıcının yeni taslak başlatmasına izin verir. Bu ayrıntı ilk uygulama varsayımıdır.

Bir ilanda en fazla bir açık revizyon (`draft` veya `submitted`) bulunur. Gönderilmiş revizyonun içerik alanları değiştirilemez. Düzeltme için önce geri çekilir, ardından yeni taslak oluşturulur. İçerik ve dosyalar revizyon bazında sabittir; yalnız değerlendirme metadatası ve durum değişebilir.

İlk onay ilanın public sürümünü oluşturur. Yayındaki ilanın yeni taslağı/gönderimi public sürümü etkilemez. Ret veya geri çekme eski public sürümü değiştirmez. Yeni onay, Listing satırı üzerinde kısa transaction ve eşzamanlılık kontrolüyle public pointer'ı değiştirir.

Aynı revizyonun tekrar onaylanması ikinci fiyat geçmişi veya olay oluşturmaz. Geri çekilmiş, eski veya yanlış ilana ait revizyon yayımlanmaz. İlanın public sürümü başka bir Listing'e ait olamaz. İlk yayım zamanı sonraki açıklama düzenlemelerinde değişmez.

Fiyat Decimal olarak, para birimiyle birlikte tutulur. İlk yayımlama fiyat başlangıcını belirler. Sonraki gerçekten yayımlanan fiyat/para birimi değişiklikleri önceki ve sonraki tutar/para birimiyle PriceChange kaydına yazılır. Para birimi değişimi fiyat düşüşü olarak değerlendirilmez.

Her yayımlanan revizyon için benzersiz `listing.revision_published` olayı oluşur. İlk yayımdan sonraki fiyat değişimi için ayrıca benzersiz `listing.price_changed` olayı oluşur. Unique anahtar `(event_type, revision_id)` olur. Outbox satırı aynı transaction içinde kaydedilir.

## Public görünürlük

Tek sorgu politikası: lifecycle `live`, onaylı public_revision mevcut, expires_at boş veya gelecekte, ilanın/satıcının görünürlüğünü engelleyen etkin kısıtlama yok. Liste, detay, kategori, mağaza ve bildirim gönderim öncesi kontrol bunu kullanır.

Taslak önizleme ayrı, yetkili bir URL'dir. Sahip veya yetkili moderatör önizleyebilir. Public detay URL'si sahibine dahi taslağı yanlışlıkla göstermez. Taslak fotoğrafları public sürüme karışmaz.

## Kategori özellikleri

Ortak alanlar normal sütunlarda, kategori özellikleri türü doğrulanmış JSON'da tutulur. Şema anahtar, tür, birim, zorunluluk, seçenek ve filtrelenebilirlik tanımlar. Revizyon schema_version tutar. Başlangıç örnekleri: otomobilde model_year ve mileage_km; emlakta area_m2 ve room_count.

Arayüz girdisi kayıtta normalize edilir. Sayısal aralıklar ve seçenekler doğrulanır; geçersiz veri sessizce sıfıra dönüştürülmez. Filtreleme SQL'de yapılır. Sık kullanılan alanlara ölçümle uygun tipli ifade indeksleri veya arama sütunları eklenir.

## Arama ve kayıtlı aramalar

SearchSpec version, keyword, category scope, location, price range, currency, typed attributes ve sort taşır. Browse, kategori, mağaza ve kayıtlı aramalar aynı doğrulanmış eşleşme tanımını kullanır. Görsel sıralama/pagination ile eşleşme koşulları ayrıdır. Türkçe karakter ve marka/model örnekleri gerçek sorgu kümesiyle değerlendirilir.

İlk arama PostgreSQL full-text ve uygun alanlarda pg_trgm kullanır. Bildirimler listing.created_at yerine gerçekten yayımlanmış olaylara dayanır. Yalnız en büyük ID/zaman imlecine bakılarak geç commit eden olaylar atlanmaz. Public arama projeksiyonu gerekirse asıl onaylı içerikten yeniden üretilebilir olur.

## Görüşmeler

Conversation ilan ve tarafları temsil eder; Message görüşmeye bağlıdır; Participant okunma/arşiv durumunu tutar. Gelen kutusunda önce görüşmeler veritabanında sayfalanır. Yeni görüşme görünür ve iletişime açık ilanda başlar. İlan kapandıktan sonra mevcut tarafların yanıtlaması hesap kısıtları ve engelleme izin verdiği sürece devam eder.

İlk mesaj ve yanıt işlemleri merkezi yetki kontrolünden geçer. Tüm mesaj geçmişi Python'da gruplanarak gelen kutusu oluşturulmaz. İlk sürümde aralıklı yenileme yeterlidir; sürekli bağlantı ölçülmüş ihtiyaçla eklenir.

## Moderasyon ve güven

Karar; aktör, gerekçe, ilgili içerik sürümü ve zaman taşır. İtiraz yeni kayıt olarak eklenir. İlan görünürlüğü, ilan yönetimi ve mesajlaşma kısıtları ayrı yeteneklerdir. Kararın etkisi URL isimlerine göre uygulanmaz.

Personel review izni yalnız is_staff üzerinden varsayılmaz. Pilot öncesinde personel MFA, doğrulanmış hesaplar, giriş/mesaj/yükleme hız sınırları, dosya kotası ve audit kayıtları tamamlanır. Hesap e-postası public aramaya katılmaz.

Özel kanıtlar ve orijinal yüklemeler public dosya URL'si almaz. Sahiplik kontrolü, içerik doğrulama, boyut sınırı ve güvenli türev üretimi uygulanır. İncelenmiş dosya üzerine yazılmaz. Public ilan kaldırıldığında ilgili yayın varlıklarının dağıtım/önbellek kaldırma işi de kaydedilir.

## Arka plan ve teslimat

Celery iş yürütür; Redis aktarım katmanıdır. Outbox ve NotificationDelivery kalıcı doğruluk kaynağıdır. on_commit kuyruğu uyandırabilir; bekleyen kayıtların periyodik yeniden değerlendirilmesi kurtarma yoludur. İşler tekrarlanabilir, denemeler sınırlı ve hatalar görünür olur.

Teslimat `(event, recipient, channel)` birleşimiyle tekilleştirilir. Dış sağlayıcı kabulüyle yerel sent kaydı arasındaki kesinti belirsiz sonuç yaratabilir; desteklenen provider idempotency anahtarı kullanılır ve belirsiz sonuç ayrı izlenir. Kesin tek seferlik e-posta garantisi verilmez.

## Öne çıkarma

PromotionProduct, Purchase ve Activation ayrıdır. Fiyat/süre/koşullar satın alma anında sabitlenir. Ödeme tamamlanması yayından kaldırılmış ilanı yeniden yayımlamaz. Tekrarlanan ödeme bildirimi ikinci hak üretmez. İşlenmiş kanıt sabittir. Sponsorlu yerleşimler etiketlenir. Süre sırasında ilan kapanmasının kalan hakka etkisi satışa açılmadan belirlenir.

## İlk uygulama sınırı ve sonraki paketler

İlk paket: ayrı geliştirme runtime'ı, User/Category, Listing/ListingRevision, özel yükleme ve görsel işleme, sahip taslak ekranları, yetkili inceleme, public liste/detay, ortak görünürlük, fiyat geçmişi ve outbox üretimi. E-posta eşleştirme/teslimatı bu aşamada tamamlanmış sayılmaz.

Sonraki sıra: SearchSpec ve kategori filtreleri -> görüşmeler -> canlı pilot güven/işletim kabulü -> favoriler/kayıtlı aramalar ve teslimat -> vitrin -> ücretli öne çıkarma. Eski veri aktarımı, gerçek veriye ihtiyaç saptandığında ayrı eşleme ve doğrulama planıdır.

## Doğrulama ve işletim

Yeni çekirdek gerçek PostgreSQL üzerinde test edilir. Migration drift, yetkiler, eşzamanlılık, görünürlük, revizyon sabitliği ve tekrar çalışan işler doğrulanır. Sabit uygulama imajı, kontrollü migration, web/worker sağlığı, yedek ve ayrı ortama geri yükleme pilot kabulüne dahildir. Eski repository suite ve yeni uygulama suite sonuçları ayrı tutulur.

## Teknik kaynaklar

- https://www.djangoproject.com/download/
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://www.postgresql.org/docs/17/datatype-json.html
- https://www.postgresql.org/docs/17/pgtrgm.html
- https://docs.celeryq.dev/en/stable/userguide/tasks.html
- https://htmx.org/docs/

Bu kaynaklar kullanılan mekanizmalar içindir; ürün kuralları bu şartnamenin tasarım kararlarıdır.
