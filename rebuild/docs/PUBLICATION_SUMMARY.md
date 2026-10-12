# Yayın özeti ve işletim sınırları

Bu paket kabul edilmiş ürün byte'larını ve operasyon kaynak kodunu yayımlar; yerel makbuzları, runtime/baseline envanterini veya yedekleri yayımlamaz. Ayrıntılı yerel kabul kayıtları GitHub paketine dahil değildir. Manifestteki tarihsel ürün belgeleri byte değiştirilmeden korunmuştur; dışarıda kalan yerel makbuz bağlantıları yalnız açık yokluk bildirimlerine gider. Bu bildirimler özgün rapor veya PASS yerine geçmez.

## Kaynak kapsamı

319 ürün dosyası exact kabul hash'leriyle taşınır. Operasyon kodu ve gerekli kaynak bağımlılıkları ayrıca listelenir; toplam sayı [yayın dosya listesinde](PUBLICATION_FILES.json) ayrılır. Yeni clone'da operasyon gate'leri yerel makine kimlikleri, korunan anahtar referansları, araç pinleri ve yayımlanmayan bağımsız kabul kanıtları olmadan geçmez. Kodda bu bağlar korunur; boş baseline/sahte PASS ile tamamlanmaz.

Operasyon girişi `node rebuild/ops/phase14-operations/run.cjs`; varsayılan developer gözlemidir. Observe/media/capture-preflight/capture-original/restore-original alt komutları vardır. Bu yayın hiçbirini veri işlemi amacıyla çalıştırmaz. Yeni clone'u çalışan yerel ortam saymayın.

## Ortamlar

`<PROJECT_ROOT>` asıl uygulama, `<DEVELOPER_ROOT>` geliştirme köküdür. ORIGINAL bağlamı base Compose + compose.original-notifications.yaml, proje classifieds-rebuild/loopback8088; developer bağlamı base + compose.dev.yaml, classifieds-rebuild-dev/loopback8089. Overlay ayrı deployment kaydıdır; yalnız base ile yeniden oluşturma bildirim etkinliğini kaybettirebilir. Bu PR hizmet başlatma/deployment talimatı değildir.

## Dışarıda kalanlar

Özel ortam dosyaları, credentials/OTP/session/anahtar zarfları, dump/gerçek medya, şifreli repository/image arşivleri, before kopyaları, runtime/koruma envanterleri, ham log/ekran görüntüleri, cache ve pyc yayımlanmaz. rebuild/backend/media içindeki kabul edilmiş Python uygulama kodu ürüne dahildir.

## Doğrulama

12 Ekim 2026 yayın hazırlığında tek taze developer Django koşusu: **657/657** (native/araç exit 0; test runner 192,210 saniye). Pip check, Django check, migration drift ve pending kontrolleri exit 0. Tek taze tam Node operasyon koşusu: **366/366**, skip 0 (native/araç exit 0; 9,294 saniye). Yeni migration, deployment, browser fixture veya backup/restore çalıştırılmadı. Yerel testler GitHub CI PASS'i değildir. Workflow GitHub-hosted ubuntu üzerinde izole test ortamı kurar; production deployment, self-hosted runner veya secret erişimi yoktur.

Yayın biçim farkı: yalnız schema_semantics.py test kaynağındaki üç boş satırın boşlukları ve arama tasarımı belgesinin son boş satırı yayın kopyasında temizlendi. Kaynak çalışma alanları değişmedi. Eski operasyon PASS bu farklı yayın byte’larına taşınmış sayılmaz; özgün/yayın hash farkı dosya listesinde belirtilir. .gitattributes, kabul edilmiş CRLF byte’larını whitespace hatası sanmadan gerçek boşluk kontrollerini korur. Kaynak constraint JSON sözleşmesi de pakete dahildir.
