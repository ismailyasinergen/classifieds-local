# İki adımlı doğrulama — geliştirici kabulü

## Güncel durum
MFA'nın gerçek tarayıcı kabulü izole `classifieds-rebuild-dev` uygulamasında tamamlandı. Son koşu `c28831a0c098bfe4`: **PASS, 1503 assertion, 99 gerçek HTML form POST'u, 12 ayrı ek HTTP kontrolü, 15 geçici tarayıcı context'i ve 9 güvenli ekran görüntüsü**. Komut normal tamamlandı; gerçek çıkış kodu 0. Masaüstü 1440px, mobil 390px ve JavaScript kapalı 1440px aynı senaryoları çalıştırdı. Bu sonuç asıl 8088 uygulamasına aktarım, bağımsız son inceleme veya üretim hazırlığı anlamına gelmez.

Tekrarlama, yalnız mevcut izole worktree kökünden:

```bash
node --test --test-reporter=spec rebuild/browser-tests/mfa.test.cjs
node rebuild/browser-tests/mfa.cjs
```

`--mode=desktop`, `--mode=mobile` veya `--mode=nojs` yalnız ilgili modu çalıştırır. Eski `journey.cjs` asıl uygulamayı hedeflediğinden burada kullanılmaz. Test aracı yalnız sabit `http://localhost:8089` origin'ini kabul eder; kök/Compose/servis/port/kaynak bind/DB/Redis/volume/network ayrımını doğrulamadan veri oluşturmaz. Yeni test hesapları, kategorisi ve ilanları sentetiktir; mevcut hesaplar alınmaz, silinmez veya değiştirilmez. Önceki koşuların verileri geliştirici veritabanında kalır. İnceleme kuyruğunda sonraki sayfalar olağan arayüzden takip edilir.

## Hesap kullanımı
Güvenlik menüsü `/accounts/security/` adresini açar. Staff, superuser ve etkin `listings.review_listingrevision` iznine sahip hesaplarda e-posta doğrulaması, TOTP cihazı ve o oturuma ait geçerli faktör doğrulaması zorunludur. Grup üzerinden yetkili fakat staff olmayan inceleyiciler de kapsamdadır. MFA, bulunmayan inceleme veya yönetim yetkisini kazandırmaz. Olağan satıcı hesabında MFA isteğe bağlıdır; etkinleştirilirse sonraki giriş ikinci faktörü ister.

Kendi hesabınızda Güvenlik → Doğrulama uygulamasını eşleştir yolunu izleyin. Karekodu telefonunuzdaki uygulamayla okuyun veya eşleştirme anahtarını elle girin; altı haneli kodla tamamlayın. Anahtarı, karekodu, parolayı veya ekranı paylaşmayın. Eşleştirmeden sonra gösterilen on adet sekiz haneli kurtarma kodunu hemen çevrimdışı ve güvenli saklayın. Kodlar yalnız bir kez gösterilir; tekrar görüntüleme/indirme yoktur.

Her kurtarma kodu tek kullanımlıktır. Son tarayıcı koşusu aynı kodun **kod kümesi yenilenmeden önce** tekrar kullanılamadığını ve aynı kümenin başka kullanılmamış kodunun çalıştığını ayrı ayrı doğrular. Yenileme, daha önce hiç kullanılmamış olanlar dahil eski kümenin tamamını geçersiz kılar. Yeni kodlar yine yalnız bir kez gösterilir.

Oturum doğrulaması en fazla sekiz saat geçerlidir. Kod görüntüleme/yenileme ve cihaz kaldırma için son beş dakika içinde ikinci faktör gerekir. Cihaz değişiminde eski cihazı kaldırıp yenisini eşleştirin. Arada zorunlu hesap işlemleri durur. Önceden açık moderasyon formu 403 ile reddedilir; sonradan eşleştirme formu otomatik tekrar göndermez. Yeni cihaz eşleşince eski cihaza bağlı diğer oturumlar yeniden doğrulama ister. Cihaz ve bütün kurtarma kodları kaybolduğunda otomatik atlama, acil parola veya operatör gizli geçidi yoktur; ayrı kimlik kurtarma süreci gerekir.

## Gerçek tarayıcı kapsamı
Her üç mod personel, staff olmayan grup inceleyicisi ve isteğe bağlı MFA kullanan satıcı hesaplarını gerçek parola/CSRF formuyla çalıştırdı. Yanlış TOTP, aynı zaman dilimindeki TOTP tekrarı, parola sonrası henüz tamamlanmamış giriş, kurtarma tek kullanımı, yenileme, cihaz kaldırma/yeniden eşleştirme, eski formun etkisiz kalması, gerçek ikinci oturumun geçersizleşmesi ve yeni onay işlemi doğrulandı. Satıcının MFA öncesinde kendi ilanlarına ulaşabildiği ve isteğe bağlı etkinleştirmeden sonra ikinci faktör istendiği de doğrulandı.

99 POST gerçek klavye Enter veya fare/touch benzeri pointer etkileşimiyle gönderildi. 12 ek kontrol tarayıcı-context HTTP istemcisinden yapıldı ve UI sayısına katılmadı. Yerel admin POST yönlendirme saldırı sınırı Django/CSRF regresyonlarında ayrıca testlidir; tarayıcıdaki admin ek kontrolleri GET'tir.

Form etiketleri, görünür klavye odağı, yatay taşma olmaması ve anlaşılır Türkçe hata metinleri denetlendi. Güvenlik yanıtları `private, no-store`, `nosniff` ve `Referrer-Policy: same-origin` taşır. Önceki `no-referrer` başlığı gerçek form POST'unda `Origin:null` ürettiğinden kaldırılmıştır; null/başka-origin veya eksik CSRF tokenı kabul edilmez.

## Sırlar, anahtarlar ve işletim sınırları
Sentetik parolalar, TOTP anahtarı/kodları, kurtarma kodları, cookie/session/CSRF ve imzalı test sahiplik belgesi yalnız işlem belleğinde tutulur. Trace/HAR/video veya ham framework hata çıktısı yoktur. HTTP origin izin listesi ilk gezintiden önce açılır. Görseller yalnız doğrulama tamamlandıktan sonraki güvenlik özetinden, hassas element ve görünür sır taramasından sonra alınır. Son koşunun dokuz PNG'si native dosya okuma aracıyla gözle incelendi: görünen metin okunur, mobil yerleşim sarar, QR/anahtar/kod/parola içermez. JavaScript kapalı görseller 1440x1000 görünüm alanını belgeliyor; tam sayfanın her pikseli için ayrı bir iddia değildir.

MFA verisi mevcut Django SECRET_KEY'den türetilmiş anahtarla şifrelenir. Veritabanı yedeği tek başına şifreli faktörleri geri açmaya yetmez: anahtar ve gerekli SECRET_KEY_FALLBACKS ayrı güvenli yedek/rotasyon yönetiminin parçası olmalıdır. Hiçbir anahtar bu belgelere veya test çıktısına yazılmaz. Eski anahtar kaldırılmadan önce geri yükleme ve yeniden şifreleme politikası ayrıca doğrulanmalıdır.

Paylaşılan Redis güvenlik cache'i erişilemezse faktör doğrulaması sessizce yerel cache'e dönmez; uygun private503 döner. Bu testler cache'i temizlemez. Olağan testler izole bellek cache'i, gerçek Redis regresyonları yalnız kendilerine ait benzersiz anahtarlar kullanır.

İlk devam koşusunda Gunicorn'un HTTP isteği henüz okunmadan worker timeout'u gözlendi. Son runner boşta açık context sayısını azaltır; bu, üretim ağ/ingress dayanıklılığı veya yük testi değildir. Proxy, eşzamanlılık, yedek/restore, işletim gözlemi, şikâyet/itiraz ve operatör hesap kurtarma süreçleri ayrı kabul başlıklarıdır.

## Kanıt ve devam
Ayrıntılı geçmiş: `phase5/task-B-report.md`, `phase5/browser-resume-findings.md`, `phase5/task-B-browser-completion.md`. Son JSON ve dokuz PNG: `rebuild/test-artifacts/mfa/c28831a0c098bfe4/`. Kaynak hash'leri: `phase5/task-B-source-manifest.json`.

Kaynak kodu gözden geçirmesi bu oturumda controller tarafından yapılmıştır; bağımsız ikinci inceleyici sonucu diye sunulmaz. Asıl uygulamaya aktarım öncesinde son bütünleşik inceleme, image/kaynak eşleşmesi, geri dönüş yakalaması ve asıl kullanıcı verisi/çalışma ağacı koruma kontrolleri hâlâ ayrı adımlardır.
