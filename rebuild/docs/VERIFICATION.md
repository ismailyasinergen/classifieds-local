# Doğrulama — bağımsız Classifieds Local çekirdeği

## Sonuç ve inceleme durumu

Güncel final dalga kanıtı **53 focused / 155 full NEW test PASS** ve yeniden build edilmiş image/gerçek worker smoke sonucudur; aşağıdaki ayrı bölümde exact komutlar ve sınırlar kayıtlıdır. Önceki Task6, onaylı `5_fix1` kaynak tabanı üzerinde **137 hedef / 79.290s** ve **149 full / 83.889s** geçti; bu sonuçlar tarihsel kanıt olarak korunur.

Approved6 bütün kaynak incelemesi Spec PASS, Quality CHANGES REQUIRED; 0 Critical/Important ve 9 Minor verdi. Root tek konsolide final dalgasını yetkilendirdi. **Final düzeltme bağımsız scoped incelemesi Spec PASS / Quality APPROVED; F1–F9 ADDRESSED, L1 accepted unchanged; yeni 0 Critical / 0 Important / 0 Minor.** Sonuç [final-fix-review.md](implementation/final-fix-review.md) içinde kayıtlıdır. Task6 bağımsız scoped incelemesi Spec PASS / Quality APPROVED; Task5 I1 de ADDRESSED / Spec PASS / Quality APPROVED olarak korunur. Önceki scoped sonuçlar final düzeltme verdict'i yerine geçmez.

Kaynaklar kasıtlı olarak uncommitted durumdadır. Commit/tag/push/merge/dağıtım yapılmadı. Yeni çekirdeğin doğrulanması tüm ürün veya repository checkpoint tamamlandı iddiası değildir. Eski suite ayrı olarak **NOT RUN** durumundadır.

## Tek final bulgu dalgası — güncel kanıt

2026-10-09 UTC tarihinde root'un açık execution release'iyle tek konsolide düzeltme dalgası çalıştı. Approved6 kaynağının bütün incelemesi **Spec PASS / Quality CHANGES REQUIRED**, **0 Critical / 0 Important / 9 Minor** sonucu verdi; aşağıdaki maddeler bu dalgada düzeltildi veya açık sınır olarak kabul edildi. Düzeltmelerin bağımsız scoped incelemesi **Spec PASS / Quality APPROVED**: F1–F9 ADDRESSED, L1 accepted unchanged; yeni 0 Critical / 0 Important / 0 Minor. Bu bağımsız verdict [final-fix-review.md](implementation/final-fix-review.md) içindedir; uygulayıcı testleri ayrı kanıttır.

| Gerçek final-dalga komutu | Gözlenen sonuç |
| --- | --- |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py test catalog.tests.test_validation media.tests.test_processing listings.tests.test_ui_contracts --verbosity 1` | **53 test / 21.791s / OK** |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py test --verbosity 1` | **155 test / 84.969s / OK** |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py check` | No issues (0 silenced) |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py makemigrations --check --dry-run` | No changes detected |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py migrate --check` | Exit 0; bekleyen migration yok |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python -m pip check` | No broken requirements found |
| `git diff --check` | Exit 0; untracked kaynaklar ayrıca aşağıdaki manifest ile kontrol edildi |

Altı yeni gerçek DB/HTTP/görüntü regression'ı production editlerinden önce **6 test / 12 assertion failure / 3.268s / exit 1** verdi. Generator boş sonuç, palette/index ve palette/alpha ile RGB tRNS'nin beyaz yerine kaynak rengi vermesi, U+00B2 ve 5000 basamaklı category query'nin 500 dönmesi, invalid-filter normalizasyonu ve iki kopya metni gözlendi. Generator'da tüm girişin validation kontrolü ile mevcut RGBA pozitif kontrolü zaten geçiyordu. Son GREEN bu kontrolleri ve önceki modül davranışını birlikte kapsar. PostgreSQL medya race'i farklı iki backend PID, her thread için lock_timeout=5s/statement_timeout=10s, barrier=5s/future=15s ve finally bağlantı kapatma ile aynı gerçek tek-derivative/tek-attempt davranışını korur.

Tüm NEW suite bu dalgada **bir kez** çalıştırıldı. Task6'nın 137-hedef suite'i yeniden çalıştırılmadı; 155 full suite aynı app'leri ve altı yeni regression'ı içerir. İki GREEN suite'teki intentional broker-failure recovery uyarısı bekleniyordu; error/failure yoktu. Yeni migration veya bağımlılık değişikliği yapılmadı.

Processor değiştiği için `docker compose -f rebuild/compose.yaml -p classifieds-rebuild build web` gerçekten exit 0 verdi; backend COPY katmanı yenilendi, hash-enforced bağımlılık katmanı mevcut cache'ten kullanıldı. Yeni image Id/manifest-list **sha256:112f9056e01531e86428baca5ec861f8c2c53a89c4a3e0173859b6a6d41701e7**, build manifest **sha256:6f7fc926959bd97c77c665f72ffac230fbd9bd6228e141507ee99bb0cbfdd3f7**, build config **sha256:a2205c6811905e44572c2f68ae50347f35513220599d7c8e21fb7dae83c3ed30**.

Yalnız yeni web/worker/scheduler, `docker compose -f rebuild/compose.yaml -p classifieds-rebuild up -d --no-build --wait --wait-timeout 120 web worker scheduler` ile yenilendi; DB/Redis running olarak kaldı. Safe inspect üç servisin yeni image Id'sini doğruladı. `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py smoke_media_worker --timeout 30` **exit 0**: sentetik asset 8 ready, attempts=1, gerçek metadata-free JPEG var, link_count=1; gerçek replay sonrası aynı sonuç kaldı. Filtreli worker log'u replay task ID `82750efb-9237-495a-a443-240dfb75f154` için received/succeeded kaydetti. Bu smoke mevcut RGB fixture üzerinden değişen processor'ın worker integration'ını doğrular; palette/tRNS pixel doğrulaması encoded PNG → gerçek decoded JPEG regression'ındadır.

Worker ping bir online node/pong; health `{"status": "ok"}`; root HTTP **200**. Son sinyal zamanı **2026-10-09 02:08:31 UTC**. Sentetik smoke kayıtları temizlenmedi. Task6'nın aşağıdaki image/hash/izolasyon kanıtı tarihsel olarak korunur. Root ayrıca **2026-10-09 02:10:37 UTC** tarihinde current local image'ı bind mount ve ağ olmadan read-only Python file-hash probe ile bağımsız karşılaştırdı: **109 host/image backend relative path + SHA256 çifti / 109 exact / 0 mismatch**. Bu probe Django çalıştırmadı. Root'un bağımsız GET kontrolleri de /health/ 200/expected ok ve / 200/expected Classifieds Local content verdi; uygulayıcı aynı geniş hash probe'unu tekrar çalıştırmadı.

Saved final CI'nin **12 step / 11 run block**'u tekrar `bash -n -c` ile syntax-valid bulundu. Yeni gate, tam **120 dosyalık** actual kaynak/deliverable manifest'ini (backend + açık packaging/runtime/browser/onboarding/workflow yolları) no-index diagnostic-aware tarar; implementation raporları/snapshot'ları dışarıda tutar. Mevcut manifest ve clean ignored fixture kabul edildi; trailing whitespace ve blank-at-EOF fixture'ları diagnostic ile **exit 1** reddedildi. Clean nonempty dosyanın alttaki no-index sonucu **exit 1 / 0 diagnostic character**; iki hatalı dosyanın alttaki exit 3 sonucu reddedildi. Fixture'lar yalnız ignored test-artifacts içindedir; stage/commit/cleanup yoktur. Remote CI **NOT RUN**.

## Task6 tarihindeki Django ve paket kapıları

Her Django komutu tam yeni Compose prefix'i ile yeni `web` container'ında çalıştı:

| Gerçek komut | Gözlenen sonuç |
| --- | --- |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py migrate --noinput` | Tüm yeni app migration'ları listelendi; No migrations to apply |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py setup_local --domain 127.0.0.1:8088` | Geliştirme kategorileri hazır; mevcut şemalar korundu; Classifieds Local yerel kurulumu hazır |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python -m pip check` | No broken requirements found |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py check` | System check identified no issues (0 silenced) |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py makemigrations --check --dry-run` | No changes detected |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py migrate --check` | Exit 0; bekleyen migration yok |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py test catalog listings media moderation --verbosity 1` | 137 bulundu/çalıştı; OK; 79.290s |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py test --verbosity 1` | 149 bulundu/çalıştı; OK; 83.889s |

Test runner yalnız yeni DB servisinde geçici test DB'si oluşturup normal test sonunda kaldırdı. İki suite'te mevcut intentional enqueue-failure testinden güvenli pending-scan uyarısı çıktı; failure veya error yoktu. Task5'in önceki 25/149 sayılarını final Task6 sonucu olarak devralmadık; yukarıdaki sayılar bu görevde gerçekten çalıştırılan komutlardır.

Bu son migration çalıştırması zaten hazırlanmış yeni DB üzerinde doğrulamadır; Task1'in ilk migration uygulamasını yeniden yapılmış gibi sunmaz. Yeni kalıcı geliştirme verileri veya sentetik browser fixture'ları temizlenmedi.

## Task6 tarihindeki image, lock ve kaynak paketleme

Gerçek komut:

```bash
docker compose -f rebuild/compose.yaml -p classifieds-rebuild build web
```

Build exit 0. Mevcut backend COPY katmanı yeniden oluşturuldu; hash zorlayan pip kurulum katmanı mevcut cache'ten kullanıldı. Bu çalıştırma yeni bir resolver veya bağımlılık upgrade'i değildir. Task1'in gerçek hash-enforced kurulum kanıtı, korunmuş lock ve aşağıdaki current-image kontrolleri birlikte değerlendirilir.

| Ölçüm | Gerçek değer |
| --- | --- |
| Docker client/server | 29.7.2 / 29.7.2 |
| Compose | v5.3.1 |
| Image platform | linux/amd64 |
| `docker image inspect` Id | `sha256:50ab956e550d7e913f4cb8dc6a746fb3810697e70e7327b8a1146e1688b4fe22` |
| Build image manifest | `sha256:56e379bd4b5e1908eea6bca86ca7369b8db00db2c9285de2630b4bf440b9d9d8` |
| Build config | `sha256:fb77952b1e95533e9f6a5e9c66ef652d4af1918ca6a6d35d1ca2c52be3fc92c2` |
| Host ve image lock SHA256 | `2653102360576a43ce1bbc427bcbac0363bafc2e72b9cc65f2ec38b6c8cc5f5d` |
| Lock paket sayısı | 26; gerçek pip list ile 26/26 sürüm eşleşmesi; ilave yalnız base image pip 25.0.1 |
| Backend kaynak dosyası | Host 109, mount'suz image 109; tüm relative path/SHA256 çiftleri aynı |
| Onaylı kaynak tabanı | `source-snapshot-index.json` → `5_fix1`, 117 dosya / 14 part |

109 backend dosyasının image kontrolü `docker run --rm --entrypoint python classifieds-rebuild-web:local -c "..."` ile yalnız dosya inventory/hash okuyarak yapıldı; kaynak bind mount'u kullanılmadı, Django komutu çalıştırılmadı. Host inventory `find ... -exec sha256sum ...` ile okundu. Onaylı 117 dosyanın snapshot içeriği actual kaynaklarla karşılaştırıldı. Native read sınırını aşan tek satırlı HTMX için snapshot içeriğinin SHA256'sı actual host hash'iyle karşılaştırıldı: `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717`. Backend ve ignore/lock/runtime kaynaklarına Task6 değişikliği yapılmadı.

Sabit base image referansları:

| Image | Digest |
| --- | --- |
| `python:3.12.15-slim-bookworm` | `sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258` |
| `postgres:17.11-bookworm` | `sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826` |
| `redis:7.4.11-bookworm` | `sha256:4fa24486b8bcca8eec45ee0eb166edc674795e53a2b53d1a9ef263eecebaac85` |

Docker context yalnız `rebuild/` içindedir. `.dockerignore` yalnız Dockerfile, lock ve backend'i alır; bytecode/cache'i dışlar. Image'da tam kaynak inventory eşleşmesi, legacy/vendor/docs/test-artifacts veya beklenmeyen backend runtime çıktısı olmadığını bu mevcut build için gösterir. Backend allowlist'i gelecekte eklenebilecek yanlış runtime dosyasını otomatik tanımaz; CI'nin packaging adımı ortam/DB/coverage/bytecode/log dosyalarını ayrıca reddeder.

`git check-ignore -v`, media source/migration için scoped negation'ı; cache, local environment, browser dependency ve screenshot yolları için intended ignore kurallarını doğruladı. Normal Git untracked inventory bütün **18 media Python source** dosyasını içeriyor. Task5'in önceki ignore regresyonu çözülmüş durumda kaldı.

## Task6 tarihindeki servis ve izolasyon kanıtı

Yalnız yeni `web/worker/scheduler` şu komutla current image'a geçirildi:

```bash
docker compose -f rebuild/compose.yaml -p classifieds-rebuild up -d --no-build --wait --wait-timeout 120 web worker scheduler
```

DB ve Redis zaten çalışan yeni proje servisleri olarak kaldı. Bridge veya legacy runtime değiştirilmedi.

| Kapı | Gözlenen sonuç |
| --- | --- |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild ps` | db/redis/web healthy; worker/scheduler running |
| `docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web celery -A config inspect ping --timeout 5` | Bir gerçek worker node'u OK/pong |
| `curl --fail --silent --show-error http://127.0.0.1:8088/health/` | HTTP başarı; `{"status":"ok"}` |
| Root HTTP isteği | `http://127.0.0.1:8088/` → 200 |
| Yeni DB read-only SQL | current_database `classifieds_rebuild`; PostgreSQL 17.11 |
| Web host port | Yalnız `127.0.0.1:8088 -> 8000` |
| DB / Redis host portu | Yok; inspect binding null |
| Yeni app source mount | Onaylı worktree `rebuild/backend -> /app`, writable=false |
| Container project label | Beş serviste `classifieds-rebuild` |

Gerçek named volume'ların tamamı `com.docker.compose.project=classifieds-rebuild` label'ına sahiptir:

- `classifieds-rebuild_rebuild_postgres`
- `classifieds-rebuild_rebuild_redis`
- `classifieds-rebuild_rebuild_media`
- `classifieds-rebuild_rebuild_static`
- `classifieds-rebuild_rebuild_scheduler`

Yalnız safe image/mount/label/port alanları inspect edildi; full env/config veya kimlik bilgileri dökülmedi. Son açık zaman ölçümü: **2026-10-09 01:43:50 UTC**, DB/volume/port kanıtları alındıktan sonra.

Task6 aşamasındaki Celery ping erişilebilir worker kanıtıydı; tek başına medya işi işlendi veya beat dispatch geçti iddiası değildir. Task3 gerçek worker/replay/scheduler kanıtını kaydetti. Task6 o aşamada değişmemiş processor için yeni smoke yapmadı. Daha sonraki final dalgada processor değişti; yukarıdaki yeni image/servis refresh ve gerçek worker/replay smoke ayrıca çalıştı. Beat dispatch bu final dalgada yeniden ölçülmedi.

## Browser ve görsel kanıtın zamanı

Task5'in gerçek Chromium journey'si **144 assertion**, örneklenmiş rendered sunum denetimi **20 assertion** ile geçti. Yedi gerçek product screenshot farklı journey aşamalarını gösterir. Root bunları bağımsız görüp Windows kaynaklarıyla byte count/SHA256 eşleştirdi.

Screenshot'lar daha sonra yapılan input-border ve embedded heading düzeltmelerinden önceki aşamaları gösterir; nihai tüm piksellerin yeniden çekildiği iddia edilmez. 144 assertion'lık journey, final I1 form-option düzeltmesinden önceye aittir. I1 ise gerçek DB-backed details GET/POST ve sekiz representation/control case içeren RED/GREEN regression ile kapatılmıştır. Task6 ve final düzeltme dalgası browser, screenshot veya browser fixture provisioning'i tekrar çalıştırmadı. Final category/copy değişiklikleri gerçek rendered HTTP regression'larıyla kapsandı; orijinal screenshot'lar değişmedi. Örneklenmiş sunum assertion'ları kapsamlı accessibility sertifikası değildir.

## CI — yazılmış ve statik doğrulanmış, uzakta çalıştırılmamış

Yeni dosya: `.github/workflows/rebuild-ci.yml`. Root `.github` yokluğu ve applicable instruction inventory implementation öncesinde kontrol edildi; vendor workflow değiştirilmedi.

Workflow yeni Compose projesini Ubuntu 24.04 GitHub-hosted runner'da build/start eder; migrate → setup_local → worker/scheduler sırasını korur; package/tam-manifest-whitespace/check/drift/migrate/catalog-listings-media-moderation hedef/full suite/health/worker-ping kapılarını yürütür. Test sayısı workflow'da sabitlenmez; gerçek runner sonucu kaydedilir.

Checkout `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1), preflight'ta official exact-SHA action.yml/README ile doğrulanmıştır. `contents: read`, `persist-credentials: false`, `clean: false`; privileged event, self-hosted runner, publish veya deployment yoktur.

Task6 tarihindeki actual static validation: YAML parse edildi, **12 step / 11 run block** bulundu; bütün run block'ları `bash -n` ile syntax-valid. Final dalgada saved 11 run block tekrar `bash -n -c` ile denetlendi; önceki YAML parse sonucu yeni bir final parse çalıştırması olarak sunulmaz. Normal fresh-runner source packaging check'i media Python dosyalarının tracked olduğunu ve private/generated artifact bulunmadığını denetler.

Son cleanup adımı yalnız hem `GITHUB_ACTIONS=true` hem `RUNNER_ENVIRONMENT=github-hosted` ise bu yeni runner projesini kaldırır. **Yerelde cleanup çalıştırılmadı.** Remote GitHub Actions run yoktur; yazılmış/statik doğrulanmış workflow sonucu remote CI PASS olarak sunulmaz.

## Whitespace, legacy ve kaynak koruma sınırları

Task6 tarihindeki `git diff --check` exit 0/no output. O aşamada bütün rebuild kaynakları untracked olduğundan ayrıca 117 approved source ve yeni README/workflow için `git -c core.autocrlf=false diff --no-index --check -- /dev/null <file>` taraması yapıldı. Temiz nonempty dosyanın no-index exit 1'i “dosya farklı” durumudur; whitespace değerlendirmesi diagnostic output üzerinden yapılır.

Bu tarihsel Task6 taraması o aşamanın onaylı kaynağında yalnız iki **new blank line at EOF** buldu:

- `rebuild/backend/listings/models.py:88`
- `rebuild/backend/static/vendor/HTMX-LICENSE:14`

Bunlar Task6 tarafından değiştirilmedi; tek final dalgada yalnız redundant son boş satırları kaldırıldı. License wording'i korunur. Final CI manifest'inin gerçek 120 kaynak/deliverable taraması diagnostic vermedi. Değişen Task4 raporu ve final-fix-report eklendiğinde **122 dosyalık kaynak/rapor taraması exit 0 / PASS**, whitespace diagnostic veya abnormal git status yok. Bu kayıtların final native write/readback'inden sonra aynı gate documentation freeze için tekrar doğrulanır. Tarihsel Task6 sonucu untracked kaynakların o aşamada tamamen temiz olduğu iddiasına dönüştürülmez.

Eski suite durumu: **NOT RUN; başarısız olarak etiketlenmez.** Çalıştırılmayan exact legacy komut:

```bash
docker compose exec -T web python manage.py test --verbosity 1
```

Eski runtime, DB ve medya bu görevin dışındadır; onları başlatmak/yeniden hazırlamak veya değiştirmek yetkili değildir. Yeni suite başarısı legacy suite başarısını kanıtlamaz.

Preservation audit, original HEAD/branch eşleşmesi ile gözlem anındaki 158 entry'yi (50 unstaged tracked modification + 108 untracked) kaydeder; stage/delete/rename gözlenmemiştir. Tam initial status-name/content-hash inventory yoktur. Bu nedenle original kullanıcının modified/untracked kaynakları için byte-for-byte önce/sonra koruma iddiası yoktur. Task6 original checkout'a erişmedi; approved new source karşılaştırması farklı ve sınırlı bir kanıttır.

## Ertelenmiş bulgular ve pilot işleri

Approved6 whole-source triage'ı sonrasında tek final dalganın disposition'ları bağımsız scoped incelemede doğrulandı: F1–F9 ADDRESSED; L1 accepted unchanged.

| Önceki bulgu | Sınır / durum |
| --- | --- |
| Task1 M1 | FIXED: iterable validation öncesi materialize edilir; gerçek generator iki row oluşturur, geçersiz sonraki öğe hiçbir yeni row yazmaz |
| Task3 M1 | FIXED: alpha band veya transparency metadata RGBA beyaz composite yoluna girer; palette/index, palette/alpha, RGB tRNS ve RGBA gerçek pixel kontrolleri geçer |
| Task3 M2 | FIXED: fresh thread bağlantıları, per-thread PostgreSQL lock/statement timeout, distinct PID ve mevcut gerçek race assertion'ları |
| Task3 M3 | ACCEPTED SCOPED FUTURE LIMITATION: gerçek upload non-atomic/service-owned boundary doğru; gelecekte outer transaction kullanan caller file rollback compensation/reconciliation sağlamalıdır; bu dalgada service değiştirilmedi |
| Task4 M1 | FIXED DOC ONLY: Task4 raporu exact distinct price_changed keys'i söyler; price/currency bu payload'da yok, event source değişmedi |
| Task5 M1 | FIXED: bounded ASCII positive ID parse; malformed/oversized/out-of-range filter yok sayılır, selected filter boş olur; U+00B2/5000-digit/valid anonymous HTTP controls geçer |
| Task5 M2 | FIXED: privacy yalnız özel route'u anlatır; gönderme yönergesi draft-only; current approved içerik public route'ta görünür kalır |
| Task5 M3 | FIXED: yararlı kategori alanı yönergesi; concrete schema/version backend sözleşmesi değişmedi |

Task6 bu maddelerde gizli düzeltme yapmadı. Tek final dalga ayrıca iki EOF boşluğunu ve Task6 M1 CI committed-whitespace gap'ini kapattı: no-index full-file diagnostic gate, history veya çalışma ağacı diff'ine bağlı olmadan actual manifest'i denetler. Final scoped reviewer sonucu Spec PASS / Quality APPROVED; yeni 0 Critical / 0 Important / 0 Minor. Ayrıntılı bağımsız sonuç [final-fix-review.md](implementation/final-fix-review.md) içindedir.

Pilot sırası README'de açıklanır: MFA ve abuse/rate/quota; yedek/restore ve operatör kurtarma; worker/scheduler/outbox gözlemi; özel medya orphan uzlaştırması; kapsamı onaylı sonraki arama/profil/domain paketleri; ayrı canlı dağıtım hazırlığı. Harici e-posta teslimi, outbox consumer teslimatı, production güvenliği ve tam ürün kabulü kanıtlanmış değildir.
