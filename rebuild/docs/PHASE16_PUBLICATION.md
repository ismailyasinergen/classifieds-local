# Faz 16 demo öne çıkarma — yayın kapsamı

Bu yayın 15 yeni ve 7 değişen ürün/test dosyası ile 3 public belge içerir. Üç yönlü karşılaştırmada yedi uzak dosya önceki kabul edilmiş byte'larla eşleşti; 15 yeni yol uzak tabanda yoktu. Bütün klasör senkronize edilmedi.

Uzak taban: a018864fa1b95b9afee1dd573fbbf1e99b4f7b98. Yerel 334 yolluk aday: aa8667e93fc5fa323ec33c15f5c1b95c6a23c152482c39ffdd27c3702a225497. Yayın ağacı bu manifestle aynı bütün değildir. Diğer 312 ürün yolu uzak main'den korundu. Adaydan farklı tek yol .github/workflows/rebuild-ci.yml, SHA-256 73af9adda4ff1e1adcd2851afbee65eca39d960aea7dba52e6564d0450805cfc. PR #54 ile kaldırılan PR paths filtresi geri getirilmedi; push filtresi, rebuild check adı, GitHub-hosted runner ve contents:read korundu. Diğer uzak yayın düzeltmeleri korundu. PUBLICATION_FILES.json önceki Faz 15 yayınının tarihsel envanteridir.

## Demo ve işletim sınırı

PromotionProduct → değişmez Purchase snapshot → demo_no_payment kanıtı → süreli Activation ayrıdır. Genel flag kapalıdır; developer ayarı yalnız doğrulanmış developer ortamında işler. **Demo — gerçek ödeme alınmaz.** Sentetik tutar/süre gerçek ticari teklif değildir. Sahiplik, güncel e-posta/MFA, POST/CSRF, private/no-store, transaction ve benzersizlik korunur. Sponsorlu bölüm ilk arama sayfasında en fazla üç kayıt gösterir; süre/görünürlük ortak sorguda uygulanır.

ORIGINAL hâlâ Faz 14 ürünündedir; PR yerel 8088'e dağıtım değildir. promotions.0001_initial ve 0002_immutable_demo_records kaynakları yayımlanır; yayın görevi mevcut DB'lere migration uygulamaz. Faz 15 yedek/restore kabulü önceki ürüne aittir, promotions verisi için yeni kabul değildir. P14-R1/R2/R3, H5 ve tarihsel erişim/sağlık/browser/.env notları açık kalır.

## Kanıt ayrımı

Kayıtlı developer teslimi: 23 hedefli / 679 tam Django / 22 başlangıç regresyon testi; gerçek desktop/mobile/JS kapalı browser kabulü; bağımsız dondurulmuş kaynak incelemesi PASS. Bağımsız inceleyici test/runtime/browser koşularını yeniden çalıştırmadı. Bunlar tarihsel kanıtlardır; özel makbuzlar pakette yoktur. Yayın görevi browser fixture veya başlangıç/operasyon suite'ini tekrarlamaz.

12 Ekim 2026 taze yayın testleri, değişmemiş developer kaynağında demo açık: promotions modülü 22/22 (13.450 s); tam Django 679/679 (194.619 s, --parallel 2 --noinput). Pip check, Django check, migration drift ve pending kontrolü geçti. Bu görev mevcut DB'ye migration uygulamadı. Test DB/cache/mail mevcut izole runner düzenini kullandı. Tarihsel 23 hedefli sayısı bu yeni 22 testlik modül koşusuna taşınmadı.

25 staged dosyanın tamamında kaynak/byte/hash, dar gizli-değer taraması, public bağlantılar ve whitespace kontrolü geçti; ürün byte dönüşümü yok. Genel CRLF ayarı değiştirilmedi. GitHub CI gerçek yayın ağacının ayrı kanıtıdır; yerel PASS uzak CI PASS'i değildir. Uzak sonucu PR checks gösterir.

## Dosya kökeni ve SHA-256

Aşağıdaki 22 yol kabul edilmiş Faz 16 adayından gelir. README.md, CURRENT_STATUS.md ve bu özet yalnız yayın için hazırlanmış public belgelerdir. Diğer yollar doğrulanmış uzak tabandan korunur.

| Yol | Fark | Aday SHA-256 |
| --- | --- | --- |
| rebuild/backend/accounts/mfa_middleware.py | değişen | 7bc7cabd3add85d4880748fd8ab3afc1920b225fb630a28ed2ac55bc9d229408 |
| rebuild/backend/config/settings.py | değişen | ed17df9e96e7c1adfa4e64ecbf2e86165d41f4fdd7963e5c315ca5f41a4821c4 |
| rebuild/backend/config/urls.py | değişen | 6e4c3a8e7386cfb66fa001ccd189f7af1dfe3a29f0347c98c5a36d56a35fb63d |
| rebuild/backend/listings/tests/test_phase16_promotions.py | yeni | 5217f6f1fa8f0b42599432a0daeef03e8b09844dfc56fac953aacef9adfb73b7 |
| rebuild/backend/listings/views.py | değişen | 462942502fc037c6343b188bdbe52febf21936b1531fdad960d472c8aa61adbd |
| rebuild/backend/promotions/__init__.py | yeni | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| rebuild/backend/promotions/forms.py | yeni | 5925ef672238c8f1ee63a5a2ceead900b62201849ba79c3e3c9a29eeae6df7ee |
| rebuild/backend/promotions/management/commands/promotions_browser_fixture.py | yeni | ca4653ef57554f46c15963c5ee0d6a42b0e929074152bc0e37ea2ff085a9e122 |
| rebuild/backend/promotions/migrations/0001_initial.py | yeni | 57d86c86cbd5c8eb5829bc977b443701bb2ed8aff4e1f97e5c868eb4f871cd00 |
| rebuild/backend/promotions/migrations/0002_immutable_demo_records.py | yeni | 3fef2e4c18bde71d83703e2f8d1a153d788d03d03ea48963caddd3431cb5f45d |
| rebuild/backend/promotions/migrations/__init__.py | yeni | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| rebuild/backend/promotions/models.py | yeni | aeafa5871414ecc57aa8f588080121caa7fda4eee9bdde74f2adca990ba9efdb |
| rebuild/backend/promotions/services.py | yeni | 532acc445bb814fc0b543dceafabd4b89261fe846ff8c4927f4e3cee68cbd65e |
| rebuild/backend/promotions/templates/promotions/choose.html | yeni | b52fa6315353f237d6efd1e0e05fa9403741c002ad937e0fc3736d98fe10e104 |
| rebuild/backend/promotions/templates/promotions/conflict.html | yeni | 01a266af07d7ac689e6be11af2aae300cb74237619250cfd19131d6a46ac18af |
| rebuild/backend/promotions/templates/promotions/sponsored.html | yeni | 5cbce0f724904f0d2aed062b81d988f90b188d095b88d1a0cb88a5eea057ddc3 |
| rebuild/backend/promotions/templates/promotions/status.html | yeni | 1d1141d5a46cbe1a6baba895505a78d234ffec1e7099891ea25f3775ab38b46d |
| rebuild/backend/promotions/urls.py | yeni | 0dfe2e17e1fb39207ceafe5d7db9146b14477f56f340dae9f7ea9f8d3c93790d |
| rebuild/backend/promotions/views.py | yeni | 7e629593a37e88d1dc7e390f10a47c677c0b0deea3849a33458c49711a25c6ec |
| rebuild/backend/templates/listings/dashboard.html | değişen | ead561bd20c3d335c4d1f9e1253192a8913bdb08c13cca65626ac3480280eed5 |
| rebuild/backend/templates/listings/index.html | değişen | 87915a4a8ecf52b3edd142c5f1ae8e7b19eefdc315dbda679d5af2c290fe7ee9 |
| rebuild/compose.dev.yaml | değişen | d46fbd58b603ff90ab2ee80c0907e13b53d5551496e9f851bd41cdc486d4f6d4 |
## Dışarıda bırakılanlar

Özel .env/credential, cookie/session/token, DB dump ve sentetik DB içeriği, yüklenmiş medya, ekran görüntüsü, log, before kopyası, runtime/baseline envanteri ve yerel kabul makbuzları yayımlanmaz. Fixture dosyası yalnız kaynak kodudur; fixture verisi/parolası içermez. Makine yolları <DEVELOPER_ROOT>/<PROJECT_ROOT> olarak anlatılır. Main'e merge, auto-merge, dal koruması değişikliği, gerçek tahsilat, ORIGINAL aktarımı ve yeni yedek/restore yok.
