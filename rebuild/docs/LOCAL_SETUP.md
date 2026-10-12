# Classifieds Local — aktif yerel uygulama ve izole geliştirme

2026-10-09 yerel benimsemesinde kabul edilmiş çekirdek asıl repository'de etkinleştirildi. Eski backend/DB/medya kaynakları taşınmadı. Bu dosya güncel operasyonu tarif eder; Phase 1 kayıtları tarihsel kanıttır.

## İki ayrı runtime

| Özellik | Aktif uygulama | Geliştirme |
| --- | --- | --- |
| Kök | `C:\Users\ismai\Desktop\classifieds_local` | `C:\Users\ismai\.devspace\worktrees\classifieds_local-a7be577c` |
| Compose | `-f rebuild/compose.yaml -p classifieds-rebuild` | `-f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev` |
| Tarayıcı | http://127.0.0.1:8088/ | http://localhost:8089/ |
| Image | `classifieds-rebuild-web:local` | `classifieds-rebuild-dev-web:local` |
| Named volume öneki | `classifieds-rebuild_` | `classifieds-rebuild-dev_` |

Üç uygulama servisi kendi kökünün `rebuild/backend` kaynağını `/app:ro` olarak bağlar. DB/Redis host portu açmaz. Beşer postgres/redis/media/static/scheduler volume arasında kesişim yoktur. Geliştirme override'ı `!override` destekleyen Compose v5.3.1 ile doğrulandı; geliştirmede yalnız 8089 portu yayımlanır.

Aktif image ID `sha256:112f9056e01531e86428baca5ec861f8c2c53a89c4a3e0173859b6a6d41701e7` ve mevcut beş volume korunmuştur. Aktif DB/Redis yeniden oluşturulmadı; aynı kaynak kodun yol benimsemesinde aktif migration/seed çalıştırılmadı. Runtime/Compose ortamı bellek içinde karşılaştırıldı; private env dosyaları kopyalanmadı/değiştirilmedi. Güncel doğrulama [phase2/adoption-report.md](phase2/adoption-report.md) içindedir.

## Geliştirme başlangıç sırası

Worktree kökünde her komutta iki dosyayı ve `classifieds-rebuild-dev` proje adını kullanın:

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev build web
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev up -d --no-build --wait --wait-timeout 120 db redis
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev up -d --no-build --wait --wait-timeout 120 web
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py migrate --noinput
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py setup_local --domain localhost:8089
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev up -d --no-build --wait --wait-timeout 120 worker scheduler
```

Bu sıra yeni geliştirme DB'sinde uygulandı. `setup_local` Site adını Classifieds Local ve alan adını localhost:8089 yapıp geliştirme kataloğunu hazırlar; kullanıcı, parola, doğrulama veya oturum verisini değiştirmez. DEBUG/local-only ve idempotenttir, mevcut şema sürümlerini korur. Hesap kurulumu kullanıcının normal allauth akışıyla yapılır. Bu görev hesap/credential oluşturmadı.

Geliştirme tarayıcısında canonical `localhost:8089` adresini kullanın: aktif `127.0.0.1:8088` adresinin host-only cookie'lerinden ayrılır. Cookie/settings soyutlaması eklenmedi.

## Aktif uygulama işletimi

Asıl repository kökünde mevcut image ve volume'larla normal başlatma:

```bash
docker compose -f rebuild/compose.yaml -p classifieds-rebuild up -d --no-build db redis web worker scheduler
docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py check
```

Yerel kabulde /health/ ve / HTTP200, worker pong, check ve migration dry-run temiz, asıl kaynak üzerinde **155 NEW test / 81.042s PASS** doğrulandı. Geliştirmede health/root HTTP200 ve worker pong doğrulandı; aynı tam suite ikinci kez çalıştırılmadı. Commit/tag/push/checkpoint, remote CI veya eski uygulama suite'i çalıştırılmış sayılmaz. Canlı dağıtım ve legacy veri migration'ı kapsam dışıdır.

## Görünürlük, hesaplar ve test sınırı

Kategori → fotoğraflar → detaylar → özel önizleme/gönder adımları gerçek kaydedilmiş taslak kullanır. Fotoğraflar isteğe bağlıdır; mevcut olanlar işlenmiş olmalıdır. Gönderilen sürümler değişmezdir. İlanlarım güncel yayın ile bekleyen düzenlemeyi ayrı gösterir. Public URL sahibi için de yalnız güncel onaylı içeriği gösterir. İnceleme izni `listings.review_listingrevision` olmalıdır; staff tek başına yeterli değildir.

django-allauth signup/login/logout, zorunlu e-posta doğrulaması ve parola sıfırlamayı sağlar. Yerel console backend harici posta teslimi yapmaz; gerçek kullanıcı bilgileri, tokenlar ve doğrulama bağlantıları raporlara alınmaz. DEBUG-only static route yerel CSS/HTMX sunar. Private medya public statik alias'a açılmaz; onaylı fotoğraflarda exact listing/revision/asset ve görünürlük kontrolü vardır.

Tarihsel Phase 1 tarayıcı driver'ı `rebuild/browser-tests/journey.cjs` aktif 8088 proje varsayımlarını içerir. İzole 8089 browser fixture/driver uyarlaması sonraki özellik görevinin kapsamındadır; bu benimsemede driver çalıştırılmadı. Önceki gerçek browser kanıtı 144 journey ve 20 örneklenmiş presentation assertion'ıdır; güncel 8089 journey sonucu değildir. Browser doğrulamasında sentetik run-scoped hesaplar ve geçici context'ler kullanılmalı; auth log/HAR/trace/storageState veya private credential çıktısı oluşturulmamalıdır.
