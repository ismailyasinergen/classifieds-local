# Bildirim ve itiraz işletimi

Geliştirici paketi yalnız `classifieds-rebuild-dev`, localhost:8089 ve mevcut developer kaynak bağında doğrulanır. ORIGINAL8088 aktarımı bu çalışmanın kapsamında değildir. Son gerçek sonuçlar `phase6/cli-implementation-report.md` ve görev raporlarında tutulur; önceki MFA kabulü bu özelliğin kabulü sayılmaz.

## Kullanım

Güncel e-postası doğrulanmış aktif kullanıcı, başkasının yayındaki ilanını veya katıldığı görüşmede aldığı mesajı bildirebilir. Bildirim, içeriği otomatik olarak kaldırmaz. Aynı hedef tekrar bildirildiğinde önceki kayıt gösterilir; yeni açıklama eskisinin üzerine yazılmaz. Bir gönderim kimliği farklı içerikle tekrar kullanılırsa409 döner. Eski ilan sürümü tekrar bildirilmez. Kapatılmış/engellenmiş görüşmenin alınan mesaj geçmişini bildirme hakkı devam eder.

Bildirimlerim yalnız kullanıcının kendi açıklama ve inceleme durumunu gösterir. Kararlarım yalnız hakkında yaptırım uygulanan kullanıcının karar gerekçesini, durumunu ve itiraz yolunu gösterir; bildirenin kimliği/açıklaması aktarılmaz. Süresi bitmiş veya geri alınmış yaptırımın geçmişi ve itiraz hakkı korunur. Mesajlaşma kısıtı itiraz göndermeyi engellemez.

`moderation.review_reports` ve `moderation.review_appeals` ayrı yetkilerdir. Yeni inceleyici rolleri de normal parola, doğrulanmış güncel e-posta ve gerçek TOTP/kurtarma doğrulaması gerektirir. Staff işareti bu izinleri sağlamaz. Normal Güvenlik ekranından cihaz eşleştirilir; fixture cihaz veya oturum kanıtı üretmez. İlk inceleyici, bildiren ve yaptırımın muhatabı itirazı sonuçlandıramaz; işletimde iki farklı uygun inceleyici gerekir. Mesajlaşmayı kısıtlama ve bu kısıtı geri alma ayrıca `moderation.restrict_messaging` gerektirir.

İnceleyici yalnız dosyaya alınan ilan sürümü veya tek mesajın dondurulmuş kanıtını görür; bütün görüşme veya genel özel medya erişimi kazanmaz. Görseller yalnız o sürüme bağlı hazır türevlerdir. Karar gerekçesi muhataba gösterileceğinden bildirenin özel açıklaması otomatik kopyalanmaz. İtirazda yalnız kararın tam FK ile bağlı yaptırımı geri alınır; diğer yaptırımlar, kullanıcı engelleri ve ilan yaşam döngüsü korunur. Kanıt erişim audit'i içerik, parola veya MFA sırrı taşımaz.

## Sınırlar ve doğrulama

`PILOT_REPORTS_PER_DAY=20`, `PILOT_APPEALS_PER_DAY=10`: son24 saatte yeni kayıtlar sayılır; exact replay ve aynı hedefin alias gönderimi yeni kota tüketmez.429 cevabı pozitif Retry-After, bağlı alanlar ve aynı hidden token ile döner. Bu sınırlar genel trafik/DDoS koruması değildir. Kalıcı saklama/silme politikası ayrı pilot kararıdır; bu paket silme işi, dış bildirim, dosya eki, genel kullanıcı şikâyeti veya otomatik yaptırım eklemez.

```text
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test accounts.tests.test_reports_appeals_browser_fixture --verbosity 2 --noinput
node --test rebuild/browser-tests/reports-appeals.test.cjs
node --check rebuild/browser-tests/reports-appeals.cjs
node rebuild/browser-tests/reports-appeals.cjs
```

Runner, ilk gezinmeden önce origin allowlist'i ve salt okunur runtime metadata korumasını uygular. İç fixture ayrıca PostgreSQL adres/DNS, developer media volume, Site ve DEBUG sınırını doğrular; signed receipt yalnız aynı koşunun sentetik verisini inceleyebilir. Her koşu ayrı hesaplar kullanır; önceki sentetik veriler silinmez. Kaynak değiştiğinde developer uygulama image'ı build edilir ve yalnız web/worker/scheduler `--no-deps --no-build` ile yenilenir; DB/Redis yeniden oluşturulmaz.

1440px,390px ve JavaScript kapalı akışlar gerçek HTML form POST'ları kullanır. Parola, TOTP seed/kodu, kurtarma kodu, session/CSRF token ve fixture receipt süreç belleğinde kalır. Ham HTML, trace/HAR/video ve exception mesajı kaydedilmez. Durum dosyası sabit hata kategorileri ve sayımlar içerir; ekran görüntüsü yalnız allowlist'teki tamamlanmış sentetik karar/güvenlik sayfası ve sır kontrolünden sonra alınır. Görsel inceleme ayrıca raporlanır; timeout veya çalıştırılmayan kontrol PASS değildir.
