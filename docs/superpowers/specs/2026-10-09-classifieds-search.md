# Classifieds Local — SearchSpec v1 ve kategori araması

## Yetki, ürün hedefi ve kapsam

Kullanıcının 2026-10-09 tarihli yerel uygulamayı benimseme ve kalan işlere devam etme talebi, 2026-10-08 ana tasarımındaki ilk sonraki paketi uygular: arama ve kategori filtreleri. Yerel benimseme ayrı plandadır. Bu paket mevcut managed worktree ve ayrı development runtime içinde uygulanır, inceleme/testten sonra aynı kabul edilen yerel uygulamaya aktarılır. Görüşmeler, gerçek e-posta teslimatı, eski veri aktarımı, public dağıtım ve ücretli özellikler bu bağımsız arama paketinin tamamlandığı iddiasına dahil değildir.

## Global Constraints

- Geliştirme workspace ws_9c012facba; asıl aktif workspace ws_78b3cf492c. Asıl kökteki kullanıcı değişiklikleri korunur.
- Django komutlarının tamamı ilgili yeni web container'ında; geliştirme komutları docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev üzerinden çalışır.
- Çalışan uygulama classifieds-rebuild/127.0.0.1:8088 ve geliştirme classifieds-rebuild-dev/localhost:8089 ayrı image etiketleri, kaynak bind'ları ve named volume'lar kullanır.
- Kaynak yazıları yalnız native Bridge write/edit. Bash yalnız inceleme/test/build/paket işlemleri. Git commit/tag/merge/push, Bridge/tünel/auth/izinli kök ve legacy kaynak/runtime/DB/medya değişikliği yok.
- Django5.2.18/PostgreSQL17 ve mevcut lock korunur. Yeni Python bağımlılığı yok; PostgreSQL'in pg_trgm eklentisi ve Django'nun bundled postgres uygulaması gerekçeli eklerdir.
- public_listings(at=...) tek görünürlük başlangıcıdır. Aranan içerik yalnız güncel onaylı public revision'dan gelir.
- İlan satırları Python'da filtrelenmez/sıralanmaz; SQL sayfalama12, kararlı UUID son bağlayıcısı ve eager loading korunur.
- İmmutable eski kategori şemaları güncellenmez. filterable yokluğu desteklenen, zaten public gösterilen türler için legacy eligibility sağlar; explicit false engeller.
- Parola, token, cookie, özel tünel URL'si, gerçek kullanıcı/e-posta verisi çıktı ve dosyalara alınmaz.

## Kesinleştirilmiş arayüz ayrıntıları

Aşağıdaki preflight'ın arayüzleri ve davranışları bağlayıcıdır. Ek açıklamalar:

1. Parsing bütçesindeki8KiB, QueryDict'in URL-encoded UTF-8 temsilinin boyutudur;64 parametre sınırı tekrarları da sayar. En çok64 resolved schema kabul edilir; limit aşımı görünür doğrulama hatasıdır, sessiz kesme yapılmaz. Scope değerleri exact ve tree'dir. Schema/category ID'leri pozitif signed64 aralığında, schema sürümleri 1..2147483647 aralığındadır; bool kabul edilmez. Programmatic integer girdileri stringe çevrilmeden önce aralıkla sınanır.
2. API'ye validate_search_spec(spec: SearchSpec) -> SearchSpec eklenir. Manuel oluşturulmuş SearchSpec dahil tür/version/schema/bound doğrulaması için aynı ortak kurallar kullanılır. matching_public_listings bu doğrulamayı çağırır; serializer ve parser kendi kopya kurallarını üretmez. Serialization gösterim için pure primitive dönüşümü yapabilir; from_dict ve validate her kaynak/target referansını doğrular.
3. Canonical JSON bütün alanları içerir: version, keyword, category_id, category_scope, location, currency, price_min, price_max, attribute_schema, attributes, resolved_schemas, sort. Eksik/bilinmeyen alanlar reddedilir. SchemaRef nesnesi id/category_id/version; predicate nesnesi key/kind/unit/operator/value alanlarını içerir. price alanları null veya iki basamaklı decimal string, attribute decimal canonical string, integer JSON integer, boolean JSON boolean'dır. JSON ve GET currency/bounds/type kuralları aynıdır. Unsupported version sessizce v1'e yükseltilmez.
4. Typed attributes yalnız seçili exact kategoriyle kullanılabilir. tree kategorisi bütün alt düğümleri içerir, türler kategoriler arasında tahmin edilmez.
5. Decimal girişleri nokta ayracıyla, sıradan sonlu sayı gösterimidir; exponent, binlik ayırıcı ve virgül geçersizdir. Arayüz bunu sayı örneğiyle açıklar. Bu paket currency conversion veya typo/fuzzy eşleşme iddiası taşımaz.
6. Schema metadata predicates yokken canonical spec'ten atılır. Bilinen yinelenen scalar parametre hatası kuralı geçerlidir; eski category için mevcut son-değer davranışı korunur. Bilinmeyen bağımsız GET parametreleri yok sayılır.
7. Category apply yeni kategori/uygun schema kontrollerini getirir ve eski attribute/schema/resolved refs'leri temizler. Genel kriterleri korur; normal form yeni aramada page taşımaz. Hatalar escape edilmiş girilmiş değerler ve bağlı mesajlarla gösterilir; hatalı yeni aramada listing query hiç çalışmaz.
8. Listing model/publication/media/outbox davranışlarına arama dışında değişiklik yapılmaz. İndeks kurulumu asıl yeni-app DB'sine ancak developer test/review kapısından sonra uygulanır. Eski DB taşınmaz.

## Uygulama şartları

# Search preflight — SearchSpec v1

2026-10-09 teknik preflight'ından alınan normatif arama tasarımı. Kaynak rapor: rebuild/docs/phase2/search-preflight.md.

## Scope and baseline

Implement shared search, filters, stable sort, SQL pagination and Turkish mobile browse. Future product packages stay deferred. Keep the current PostgreSQL17/Django5.2.18/HTMX2.0.11 lock; only bundled postgres app and pg_trgm are added.

Workspace ws_9c012facba; root establishes project `classifieds-rebuild-dev`, loopback8089, image `classifieds-rebuild-dev-web:local` and independent volumes. Run phase2 gates in its web container; original adopted app stays separate.

Required instructions/spec/interfaces and actual catalog/listings/moderation/settings/UI/test/browser/CI sources were read. No private environment/auth/account data. Preserve public_listings as sole visibility composition, exact-category compatibility, SQL pagination12, immutable schemas and canonical decimal strings. Shared pagination also serves non-search screens; publication needs no hook.

## 1. Interfaces and ownership

Create a focused `listings/search/` package. Matching and ordering are separate; page is not in SearchSpec.

```python
@dataclass(frozen=True)
class SchemaRef:
    id: int
    category_id: int
    version: int

@dataclass(frozen=True)
class AttributePredicate:
    key: str
    kind: str                 # integer | decimal | string | boolean
    unit: str                 # stripped; absent = ""
    operator: str             # eq | gte | lte
    value: int | str | bool   # decimal: canonical string, never float

@dataclass(frozen=True)
class SearchSpec:
    version: int              # exactly 1
    keyword: str
    category_id: int | None
    category_scope: str       # exact | tree
    location: str
    currency: str
    price_min: Decimal | None
    price_max: Decimal | None
    attribute_schema: SchemaRef | None
    attributes: tuple[AttributePredicate, ...]
    resolved_schemas: tuple[SchemaRef, ...]  # frozen identities, never latest
    sort: str                 # newest | price_asc | price_desc | relevance

parse_search_spec(params: QueryDict) -> SearchSpec
search_spec_from_dict(payload: dict) -> SearchSpec
search_spec_to_dict(spec: SearchSpec) -> dict
search_querystring(spec: SearchSpec, *, page: int | None = None) -> str
matching_public_listings(*, spec: SearchSpec, at=None) -> QuerySet[Listing]
order_search_results(queryset, *, spec: SearchSpec) -> QuerySet[Listing]
```

Parsing raises field-addressable ValidationError, never a partial spec. GET/dict share normalization. JSON uses primitives, two-place prices and canonical decimal attribute strings. Reject bool IDs/versions/numbers and unsupported versions.

matching_public_listings MUST start from public_listings(at=at), not a caller queryset. Future trusted seller scope narrows by owner ID; event matching narrows by listing UUID and calls exists() without ordering/page. Conversation mutations independently recheck visibility. No private revisions/email query.

Catalog-owned functions:
```python
category_scope_ids(*, category_id: int, scope: str) -> tuple[int, ...]
category_filter_schema(*, category_id: int, schema_ref=None) -> AttributeSchema
compatible_attribute_schemas(*, source_schema, predicates) -> tuple[AttributeSchema, ...]
```

Catalog traversal uses one snapshot, arbitrary depth and a visited set. Tree includes the selected node; unknown valid category yields an empty ID set. Listing matching remains SQL.

## 2. Query-string and error contract

Endpoint remains /. Canonical ordering follows this table. Drop blank/default fields; emit v=1 for nonempty canonical search. Use QueryDict/urlencode and template escaping.

| Key | Contract |
| --- | --- |
| v | Missing=1; unsupported/malformed explicit version is an error. |
| q | NFC, trim/collapse whitespace; max200 characters; nonblank must contain a letter/digit. Plain terms, no query language. |
| category | Positive ASCII decimal, at most19 raw digits and <=9223372036854775807. Leading zeros normalize. Invalid -> no category; valid nonexistent -> zero results. |
| scope | exact default; tree includes descendants. Nondefault needs valid selected category. |
| location | Public city/area label substring, NFC/trim/collapsed whitespace, max160 characters. |
| currency | Blank=all; otherwise3 ASCII letters, uppercase. Preserve current syntax-only currency policy. |
| price_min / price_max | Inclusive Decimal(18,2), nonnegative, min<=max. Bounds require currency. |
| schema / schema_version | Exact source schema identity for attributes; both required with predicates. Schema category must match selected exact category. Independent of v. |
| schemas | Canonical comma-separated ID:version pairs, sorted. First GET without this resolves compatible schemas; canonical URLs and stored specs freeze the resolved set. Supplied refs are validated exactly; serialized attribute specs require them. |
| a.KEY.eq / a.KEY.min / a.KEY.max | Whitelisted schema key; numeric min/max map to gte/lte. eq cannot coexist with a range for that key. |
| sort | newest default; price_asc/price_desc require currency; relevance requires q. Unknown nonblank is an error. |
| page | Presentation only; reset to1 when criteria/sort change. See bounded fallback below. |

Budgets before normalization: raw query8KiB,64 parameters,20 attribute predicates,200 characters per attribute value,64 characters per raw number. Accept ordinary bounded decimal notation; reject exponent notation, NaN/Infinity and huge digit strings BEFORE Decimal/format. Scalar duplicates are errors except category retains today's last-value behavior. Ignore unrelated unknown GET keys and omit them from generated URLs; unknown a.* keys are errors. Serialized unknown keys are errors.

With no predicates, discard schema metadata from the canonical spec; it must not narrow results. Preserve recognized invalid form values, escaped, and render status200 with field errors and NO result query. Distinguish that error state from a successful zero-result search. Never silently broaden invalid new filters. Invalid legacy category remains the exception, but accompanying attributes produce a missing-category dependency error.

A bounded page parser preserves get_page semantics without converting huge spellings: missing/nonnumeric -> first; nonpositive/out-of-range numeric -> last. This is stable for a fixed result set, not a snapshot across concurrent publication.

## 3. Exact cross-version attribute semantics

ROOT DECISION: retain immutable v1; no v2 solely for flags. Omitted filterable is legacy-eligible only for supported publicly displayed typed fields; explicit false excludes. Current attributes_for displays supplied declared fields; no private/contact field is added.

The exact SOURCE schema defines predicate key/type/unit/value; reopened URLs use it, not latest. New forms may initially use latest. Serialize source AND resolved target identities.

For a fresh GET without resolved refs, inspect that category's actual schemas and freeze the resulting identities in SearchSpec. Replays validate and compile only the frozen exact refs. A candidate qualifies only if ALL requested keys exist, are eligible, and have exactly the source type and stripped unit. Never coerce integer to decimal or convert changed units. Labels, requiredness, domain bounds and option changes do not by themselves change identity.

OR candidate branches; every branch ANDs:
- public_revision.category_id == candidate.category_id;
- public_revision.attribute_schema_id == candidate.pk;
- public_revision.schema_version == candidate.version;
- ALL requested predicates under that candidate's actual rules.

A bare key/version predicate is forbidden. Missing/null/wrong JSON type fails the branch. Fresh searches include all compatible old versions. Serialized/reopened searches freeze resolved identities; newly introduced versions are not silently appended. Future saved-search refresh/migration is a separate explicit operation. Source schema is never upgraded; no cross-category inference. A key with unchanged type/unit must retain its meaning.

Range endpoints are comparisons, not stored values: normalize TYPE through normalize_attribute_value with a projected type rule. Do not reject a lower search bound merely because it is below the stored-value minimum. Guard stored values using the candidate's domain/options. Normalize equality options against that candidate; a value unavailable in one candidate eliminates that branch only. UI options may be the canonical union of compatible branches; unknown options across all candidates are form errors. Booleans remain true/false, distinct from blank and numeric0/1. Free string equality is canonical trimmed, case-sensitive equality.

Numeric extraction must use CASE: expected JSON number for integer; expected JSON string for decimal; bounded canonical numeric text; then PostgreSQL NUMERIC without narrowing precision/scale. Invalid values yield NULL. Do not rely on WHERE evaluation order to protect casts, compare decimal strings lexically, round, or filter listing rows in Python. Use literal KeyTransform/KeyTextTransform keys; even legal schema keys can contain "__", so never interpolate them into ORM lookup paths.

## 4. Text engine and minimal migration

Recommend DIRECT approved-revision expression indexes: no projection table/column, background synchronization, publication hook or media coupling.

Create a version-stable SearchFoldV1 ORM expression: NFC; map both cases of Ç/Ğ/Ö/Ş/Ü to c/g/o/s/u and İ/I/ı/i to i; handle decomposed dotted-I equivalence; lowercase. Use the identical database expression on document fields and bound query values; leave displayed text untouched. Search intentionally collapses Turkish dot/accent distinctions. Python casefold alone is insufficient for that contract.

Use PostgreSQL simple configuration with plainto_tsquery and a title(A)+description(B) weighted vector. This preserves model tokens and claims no Turkish stemming. Terms are ANDed. Keyword membership = full-text match OR literal folded-title contains when the folded query has an extractable run of >=3 alphanumeric characters. Short model terms X5/Q7 still use full-text. Location uses literal folded contains. Escape LIKE metacharacters; no user regex/raw tsquery.

One listings migration: TrigramExtension plus partial status=approved GIN indexes on:
1. Exact explicit-simple weighted SearchVector over folded title/description.
2. SearchFoldV1(title), gin_trgm_ops.
3. SearchFoldV1(location), gin_trgm_ops.

Share factories between query/model declarations; freeze v1 expression semantics for migrations. Querying UPPER/folded text against a different raw-column index is insufficient. Do not use similarity(...)>=threshold and claim operator-index support. No speculative price/attribute indexes: measure the actual query first.

All search expressions traverse the current approved public_revision. No alternative revision text, draft text/photos or account email is queried/indexed. Indexes may contain earlier approved revisions, but the current pointer and shared visibility still exclude them.

Primary sources confirm expression/configuration matching for FTS indexes and LIKE support/short-pattern limits for pg_trgm; no performance measurement is claimed:
- https://www.postgresql.org/docs/17/textsearch-tables.html
- https://www.postgresql.org/docs/17/pgtrgm.html
- https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/search/
- https://www.postgresql.org/docs/17/functions-string.html

## 5. Ordering and UI

Orders:
- newest: -first_published_at,-pk;
- price_asc: price ASC NULLS LAST,-first_published_at,-pk;
- price_desc: price DESC NULLS LAST,-first_published_at,-pk;
- relevance: -SearchRank,-first_published_at,-pk.

Literal-only title matches may have rank0. Ordering never changes membership. UUID is the final tie-breaker. Keep12/page, SQL count/limit and current revision/image prefetch. No list(queryset) before pagination, Python distinct or image N+1. Pagination encodes the validated spec once and exactly one page.

Baseline: normal GET, Turkish labels, explicit currency/ranges, false/true/blank, linked errors and reset actions. Category-apply explicitly clears old schema/attributes/resolved refs while retaining valid common criteria; no-JS action required. Never reinterpret stale controls.

At390px: one column, no overflow, wrapping labels/chips and visible focus. Preserve cards/public image route. HTMX is optional; verify error/history/back/no-JS behavior if added. No inactive future-feature buttons.

## 6. Five highest-risk regressions

| Risk | Actual result to verify |
| --- | --- |
| Privacy/publication | Current live approved row plus newer draft/submitted/rejected text, price, attributes/photo; only current values match for anonymous AND owner. Add expired/paused/closed/restricted and wrong-listing pointers. Counts agree; private email never matches. |
| Schema/type confusion | Compatible v1/v2 survive; same version in another category, mismatched schema_version, changed type/unit, explicit false, missing/null/wrong type do not. Verify decimal9/10/100, zero/false, options1.00->1. |
| Inputs/broadening | Existing category matrix, valid missing ID, duplicate scalar, unknown a.*, bad v, NaN/Infinity/1e999999/huge digits, reversed ranges, missing currency, tampered schema and "__" key. No500 or silently broadened results. |
| Turkish/model text | İstanbul/ISTANBUL/istanbul; IŞIK/ışık/isik; Şişli/sisli; Çeşme/cesme; decomposed I; Renault Clio; BMW X5; Audi Q7; Peugeot208. Actual PostgreSQL title/description/location results; multiword terms and literal %, _, quotes. |
| Pagination/mobile | >=25 equal-date/price rows give stable UUID order, nonoverlapping pages and preserved filters once. SQL count/limit and bounded eager loading.390px, keyboard/no-JS; HTMX history only if included. |

Gate: dev PostgreSQL RED/GREEN, system/migration checks, targeted/full NEW suites, complete-source whitespace and focused browser evidence. Legacy is separate. Inspect actual-query EXPLAIN before performance claims; tiny fixtures can use sequential scans. No test/EXPLAIN/runtime command ran during this preparation.

## 7. Bounded task split

A: contract/catalog. New catalog/search.py and listings/search/{__init__,specs,parsing}.py; catalog/spec/parser/round-trip tests. Freeze interfaces/error/schema semantics first.

B: PostgreSQL matching. New listings/search/{expressions,queries}.py; own model indexes, one listings migration, settings postgres registration, SQL/privacy/text/order tests. No publication/media/outbox edits.

C: browse UI. New listings/search/forms.py, filters/results templates; own views.index, index.html, isolated browse pagination context, scoped app.css and browse/browser tests. Preserve shared pagination behavior elsewhere. Depends on A and B interfaces.

Root: separate dev runtime, B/C integration, full gates, scoped independent review, INTERFACES/verification updates. CI already discovers tests; edit workflow only for a concrete gate. No commit/tag/push implied.
