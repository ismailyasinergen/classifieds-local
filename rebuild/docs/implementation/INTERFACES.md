# Shared implementation interfaces

Authoritative implementation files are linked by relative path below. This is a compact integration map, not a test report or whole-plan replacement. Tasks1,2,3,4 independently reviewed (spec PASS, quality APPROVED after scoped corrections). Read only the specific report/source needed for a concrete question.

## Runtime
Workspace ws_9c012facba; new project classifieds-rebuild. Every Django command: docker compose -f rebuild/compose.yaml -p classifieds-rebuild exec -T web python manage.py ... . Five services web/db/redis/worker/scheduler. Web published only127.0.0.1:8088 ->8000. /app source is read-only; private media/static are separate new writable named volumes. No old backend imports or old environment reads. No source file/migration generation through bash; write/edit only.

## accounts and catalog (Task1)
- accounts.User: int PK, username removed; private normalized unique email login, inherited first_name/last_name and permissions; allauth mandatory verification/console mail. Do not render email as public profile.
- catalog.Category: int PK; name,slug; optional parent PROTECT with children reverse; attribute_schemas reverse. No fixed depth.
- catalog.AttributeSchema: int PK,category PROTECT,version,definition JSON,created_at. Unique(category,version),version>=1; stored rows immutable by model/queryset/admin + PostgreSQL UPDATE/DELETE trigger. New version for changed rules.
- definition={"fields":{key:{"type":"integer"|"decimal"|"string"|"boolean","required":bool, optional min/max/options/label/unit/filterable}}}. Optional unit nonempty string; filterable strict bool. Metadata retained unchanged.
- catalog.validation.validate_attributes(*,schema,values) strict: unknown/missing required/malformed invalid; int outputs int, Decimal outputs canonical exact string. Does not mutate definition/input.
- normalize_attribute_value(*,name,rule,value) validates/normalizes one supplied field. validate_schema_definition(definition) rejects malformed declaration via ValidationError.
- seed_catalog creates Vasıta -> Otomobil and Emlak; schemas automobile(model_year,mileage_km), property(area_m2,room_count). Existing stored schema versions retained.

## listings (Task2)
Source: listings/models.py,services.py,validation.py,policies.py,queries.py.
- Listing: UUID id; owner(User,PROTECT,reverse listings); lifecycle draft/live/paused/closed; public_revision nullable FK; first_published_at/expires_at nullable; created_at/updated_at. Model clean requires public pointer belongs to same listing and approved. Task4 validates this under its lock; save alone is not the publication API.
- ListingRevision: int id; listing(PROTECT,reverse revisions); status draft/submitted/approved/rejected/withdrawn; edit_version>=1; category FK; attribute_schema concrete FK; schema_version; title200,description20000,price Decimal(18,2) nullable,currency3,location160,attributes JSON; created_at/updated_at. Images supplied by media.RevisionImage with reverse images. Meta permission listings.review_listingrevision.
- DB constraint listings_one_open_revision is partial unique listing where status in draft/submitted. Other checks cover lifecycle/status choices, positive versions and nonnegative/nullable price.
- Content keys EXACTLY title,description,price,currency,location,attributes. Categories/system/owner/public keys are not updateable through content. Partial update omits=retain, attributes supplied=replace full dict. Every successful update increments edit_version, even empty patch.
- Missing price remains None; no implicit zero/rounding; malformed/nonfinite/negative/overprecision invalid. Currency empty for partial draft or normalized three ASCII uppercase letters (syntax only). Location public city/area label; no private contact field.
- create_listing_draft(*,actor,category_id:int,content:dict)->ListingRevision: latest concrete category schema selected once; category-only draft allowed; no orphan on invalid data.
- update_draft(*,actor,revision_id:int,expected_version:int,content:dict)->ListingRevision. expected_version actual positive int. Parent Listing locked first, then child scoped/revalidated, ownership and draft/version checked before save.
- start_revision(*,actor,listing_id:UUID|str)->ListingRevision: parent lock; existing draft returned idempotently, submitted open raises InvalidRevisionState. Otherwise copy latest terminal approved/rejected/withdrawn revision and its concrete schema into a new draft. Public pointer unchanged.
- start_revision now calls media.services.copy_ready_images immediately after the new revision save inside the same locked transaction, using the exact selected terminal source; no inferred public-revision lookup.
- listings.services.StaleEditVersion and InvalidRevisionState subclass ValidationError with codes stale_edit_version/invalid_revision_state. PermissionDenied for inactive/anonymous/nonowner. Missing entities propagate DoesNotExist; malformed UUID ValidationError.
- listings.policies.require_active_actor(*,actor),require_owner(*,actor,listing) recheck DB active account. listings.queries.revision_listing_id(*,revision_id) resolves only parent UUID for later parent-first lock/recheck.
- listings.validation.normalize_draft_content(*,schema,content) and validate_partial_attributes(*,schema,values) share strict typed normalization but defer missing required fields to submit. Model clean checks schema category/version identity.

## private media (Task3)
Source: media/models.py,services.py,validation.py,storage.py,tasks.py,views.py.
- MediaAsset: int PK, owner User(PROTECT,media_assets), unique opaque UUID storage_key, original/derivative private FileFields, source_mime/source_bytes/width/height, state pending/ready/failed, attempts<=3, error_code,last_enqueued_at,processed_at,timestamps.
- RevisionImage: int PK, revision(PROTECT,reverse images), asset(PROTECT,reverse revision_images), position,created_at. Unique(revision,asset) and (revision,position); ordered position,pk.
- attach_image(*,actor,revision_id,uploaded_file)->MediaAsset; link_image(*,actor,revision_id,asset_id,position)->RevisionImage; retry_image(*,actor,revision_id,asset_id)->MediaAsset. Active owner + exact membership + draft rechecked under Listing -> revision -> asset locks. Terminal/submitted links frozen. No remove API yet; Task5 may add draft unlink preserving shared asset/files.
- require_revision_images_ready(*,revision)->None: caller MUST already hold Listing/revision locks in atomic transaction; helper locks actual linked assets in PK order and raises ValidationError for nonready/missing derivative/foreign owner/too many links. Empty images allowed.
- copy_ready_images(*,source,target)->None: internal hook inside locked start_revision transaction; copies ready same-owner links/positions from its exact selected latest terminal source; no public pointer/source changes.
- Upload allows decoded/claimed matching JPEG/PNG/WebP, actual bounded10MiB/20M pixels, max10 photos/revision. Server-chosen original/derivative names in PRIVATE_MEDIA_ROOT named volume, no public storage URL or static media mapping.
- process_image(asset_id) pending->ready/failed, asset-only row lock, one deterministic metadata-free JPEG, max1600x1600. Repeats idempotent. Persisted pending/link before on_commit enqueue; lost enqueue rediscovered by60s beat scan; bounded retry same asset.
- Private routes: media:original,media:derivative,media:status at private-media/<asset_id>/(original|preview|status)/; active owner or explicit listings.review_listingrevision only, staff alone denied. Private,no-store, safe errors/no raw paths; Task5 public derivatives must call shared visibility and actual current-revision relation.
- Upload view must let attach_image own durable transaction after form validation; no enclosing rollback-prone atomic/ATOMIC_REQUESTS. FileField file cannot roll back with an outer transaction (Task3 M3). Future enclosing workflows need scoped compensation.
- Deferred Minor findings: palette/tRNS transparency rendering and concurrency-test DB timeouts; exact findings in task-3-review.md and ledger. They are not unreported production guarantees.

## publication, moderation and visibility (Task4)
Task4 independently reviewed after I1 correction;35 focused/124 full NEW tests pass.
- listings.publication.submit_revision(*,actor,revision_id),withdraw_revision(*,actor,revision_id) -> ListingRevision. Submit requires draft and complete canonical title/description/category/concrete schema/price/currency/location/strict attributes plus all linked media ready/owned; zero photos allowed. Withdraw only submitted -> withdrawn, no content/public changes.
- moderation.services.approve_revision(*,actor,revision_id,expected_public_revision_id:int|None,reason:str),reject_revision(*,actor,revision_id,reason:str) -> ListingRevision. reason stripped1..2000 chars. Active freshly loaded user must have listings.review_listingrevision; staff alone denied, nonstaff reviewer supported; authorization rechecked on replay.
- Lock Listing -> exact revision -> assets. New approve validates state/content/readiness/current pointer, then atomically writes approved status, one decision, public pointer/lifecycle/time, optional PriceChange and unique events. No network work. Same CURRENT approved revision replay returns idempotently despite old expected pointer; superseded approved revision never reactivated.
- First approval activates draft to live; later preserves live/paused; closed blocks new approval. Successful current replay changes no lifecycle/times. first_published_at stable.
- StalePublicRevision (listings.publication) extends ValidationError code stale_public_revision. InvalidRevisionState code invalid_revision_state. Expected pointer None or positive actual int; bool/string/float invalid. Missing entities use DoesNotExist, unauthorized PermissionDenied; incomplete/schema/media/reason errors ValidationError, noncanonical stored content code noncanonical_content. Catch field error_dict or safe nonfield errors; persistence failure is not success.
- ModerationDecision (moderation.models): revision OneToOne(PROTECT,reverse moderation_decision),actor FK,outcome approved/rejected,reason,decided_at. One terminal review decision/revision; withdrawal/submission no decision. No writable review/content/history admin.
- Restriction: nullable listing/seller PROTECT with reverse visibility_restrictions, actor FK,reason,begins_at,ends_at nullable,revoked_at nullable,created_at. DB XOR target and end>=begin. Hide-public only, no management/appeal/message APIs.
- public_visibility_restrictions(*,at=None) in moderation.policies: revoked_at MUST BE NULL; begins_at<=at, ends_at absent or>at. ANY non-null revocation deactivates, including future value. at tests intervals, not full historical reconstruction; no scheduled revocation capability.
- visible_listings(*,at=None) in moderation.policies: lifecycle live; nonnull approved pointer belonging to same listing; expiry absent or strictly>at; no matching active listing/seller restriction via correlated Exists (no duplicate listings). Task5 public_listings composes this single predicate and eager loading. Every public list/detail/image uses it; image also must match exact current revision/asset relation.
- PriceChange (moderation.models): listing FK(reverse price_changes),revision OneToOne(reverse price_change),previous_revision FK,old_amount/new_amount Decimal(18,2),old_currency/new_currency,published_at. First publication no record; subsequent actual amount OR currency change one record. is_price_drop only same currency and new<old.
- OutboxEvent (events.models): event_type,revision FK(reverse outbox_events),payload JSON,created_at,processed_at nullable (future consumer only); unique(event_type,revision). Allowed event_type listing.revision_published / listing.price_changed.
- Exact publication payload keys: listing_id,revision_id,price,currency. Exact price-change payload keys: listing_id,revision_id,previous_revision_id,old_amount,new_amount,old_currency,new_currency,is_price_drop. Decimal strings exact two places, UUID listing string; no private data. price_changed does NOT additionally contain price/currency. No event consumer/delivery claim.

## Downstream rulings
- Draft -> live only on first approval. Later content approval preserves paused status; closed listings reject new approval; replay is idempotent without lifecycle change.
- Media owns MediaAsset and RevisionImage; all revision relation changes under parent -> revision -> asset order. Worker processing can lock only asset if never subsequently locking a parent.
- Public visibility exact-expiry check and active restriction policy are shared by list/detail/public media. Private preview/original and authorized derivatives use private,no-store response cache policy.

## Verification pointers
Task1 report/fix review:34 new tests passed, scoped spec/quality approved; deferred Minor M1 bulk_create(generator) in catalog recorded in progress.md.
Task2 report:28 listings +34 existing =62 full NEW tests passed;3 actual PostgreSQL races; system/migration checks passed. Independent Task2 review passed with no findings; media integration and publication remain subsequent owned tasks.

Task3 report/fix review:27 media +62 existing =89 full NEW tests passed; normal worker/replay/beat evidence in report. I1 malformed PNG exception fixed, scoped review approved; M1/M2/M3 retained for final triage.

## Task5 approved UI and query contracts (after I1 fix)
- listings.queries.public_listings(*, at=None) composes moderation.policies.visible_listings and adds related-object fetching; it does not duplicate visibility rules. Public list/detail/exact approved image relation share it.
- Public routes: listings:index /, listings:detail /ilanlar/<uuid:listing_id>/, listings:public_image /ilanlar/<uuid:listing_id>/fotograflar/<int:revision_id>/<int:asset_id>/.
- Owner routes: listings:dashboard /ilanlarim/, listings:create /ilan-ver/, listings:edit /taslaklar/<id>/duzenle/ (photos default, ?step=details), listings:preview /taslaklar/<id>/onizleme/. Submit/withdraw/start_revision/image attach/remove/retry are POST+CSRF; no GET mutation. Complete route table is in task-5-report.md.
- Review routes: moderation:queue /inceleme/, moderation:review /inceleme/<revision_id>/. Explicit active reviewer permission, SQL pagination, required reason and hidden observed expected_public_revision_id remain service-backed. Pointer/state conflicts return409 with input preserved.
- DraftForm uses the concrete stored schema, original positive edit_version, typed normalization and full attributes replacement. Nonboolean option HTML values are canonicalized through the same approved normalizer as persisted values; labels may preserve raw spelling. Boolean true/false remain explicit and distinct from blank/omitted. Invalid/stale form input is retained without saving or silently refreshing the version.
- New media.services.remove_image(*, actor, revision_id, asset_id) validates active owner/draft/exact relation under Listing -> revision -> asset locks and unlinks only RevisionImage. Shared approved assets, files and relations remain.
- UploadForm validation precedes attach_image. Resolved upload view carries non_atomic_requests for default DB and settings ATOMIC_REQUESTS is false; service owns its durable attachment transaction. Future callers adding outer transactions still need explicit compensation.
- Private preview/original/derivative and authorized public derivative enforce owner/reviewer or current approved relation as appropriate; responses use private,no-store. Original remains an attachment, private derivative is inline JPEG. Public photo checks include visible listing, exact current revision/relation, same-owner ready asset and existing derivative.
- Real HTMX2.0.11 progressive enhancement polls actual private pending-photo state; ordinary forms/navigation work without JS. Static serving is explicitly DEBUG-only in the local Gunicorn runtime. Built-in allauth forms/mandatory verification/session/reset remain intact under common branding.
- Normal local onboarding after migrate: manage.py setup_local --domain 127.0.0.1:8088. It is DEBUG/local-only, idempotently sets Site brand/domain and seeds catalog; no user/auth modification. Use this in README/CI rather than seed_catalog alone. LOCAL_SETUP.md is the task handoff.
- Browser fixture is a local DEBUG management command with captured stdin/stdout and exact run-scoped reserved synthetic identities, not a public endpoint or user onboarding shortcut. No credentials in reports or screenshots.
- Evidence after scoped fix:25 focused/149 full NEW tests pass. Earlier real browser144 journey assertions and20 sampled presentation assertions passed; seven screenshots document actual journey stages with stated later border/heading timing limits. The I1 gap has actual persisted GET/POST8-case regression coverage; no broad browser rerun was needed.
- Task5 M1 malformed Unicode category, M2 current-public preview copy and M3 seller schema/version copy remain deferred to final review; no hidden fixes or public-policy changes were made.

## Final accepted refinements
Final scoped review SpecPASS/QualityAPPROVED; allF1–F9 addressed, no new findings. No public service signature/state/authority/event contract changed. Schema bulk_create accepts generators without exhaustion while validating all inputs first. Private image derivatives composite alpha and palette/RGB transparency metadata onto white. Anonymous categoryfilter accepts boundedpositiveASCIIdecimal BigAutoFieldIDs; malformed/oversized/out-of-range filters become emptyselection/unfilteredlist. Privatepreview copy describes routeauthority and submissionguidance is draft-only. Current nonatomic attachmentserviceboundary remains required; futureoutertransactioncallers need explicit filecompensation/reconciliation. Allmedia PostgreSQL race threads nowhavefiniteDBtimeouts/distinctPIDproof. CI checks completeactualsourcecontent forwhitespace, independentofworkingtreediff. Final verification155NEW/53focusedPASS, currentworkerprocessing+replayPASS, root109backendhost/imagehashesmatch; remoteCIandlegacyNOTRUN.


## SearchSpec v1 and Turkish browse (Phase 2)

The isolated developer command prefix is `docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py ...`; its canonical browser origin is `http://localhost:8089`. The Runtime section above describes the independently adopted Phase 1 project. Actual later active-image/migration acceptance belongs to `docs/phase2/search-release-report.md`.

- Public frozen dataclasses live in `listings.search.specs`: SchemaRef(id,category_id,version), AttributePredicate(key,kind,unit,operator,value), SearchSpec(version,keyword,category_id,category_scope,location,currency,price_min,price_max,attribute_schema,attributes,resolved_schemas,sort). The package __init__ has no reexports.
- `listings.search.parsing` owns parse_search_spec(QueryDict), validate_search_spec(SearchSpec), search_spec_from_dict(dict), search_spec_to_dict(spec), search_querystring(spec,*,page=None). These retain duplicates and field-addressable ValidationError; invalid filters never become partial searches. GET/JSON/manual inputs share normalization, bounded identifiers/numbers and NUL rejection.
- `catalog.search` owns category_scope_ids(*,category_id,scope), category_filter_schema(*,category_id,schema_ref=None), compatible_attribute_schemas(*,source_schema,predicates). Exact source and compatible target identities are immutable and frozen in canonical attribute searches. Explicit filterable:false excludes; omitted flag retains supported legacy eligibility. No cross-category type/unit inference or latest-schema substitution on replay.
- `listings.search.queries.matching_public_listings(*,spec,at=None)` composes only shared public_listings and SQL filters against the current approved revision; `order_search_results(queryset,*,spec)` separately orders it. Both revalidate. Keyword uses Turkish-folded simple-config plainto full-text AND terms or eligible literal folded-title contains; location is literal folded contains. No fuzzy/stemming or currency-conversion promise.
- Orders are newest(-first_published_at,-pk), price ascending/descending(NULLS LAST,-first_published_at,-pk), relevance(-SearchRank,-first_published_at,-pk). Price bounds/sort require a3-ASCII-letter currency; relevance requires keyword. `listings.0003_public_search_indexes` installs pg_trgm plus exact approved-revision expression indexes. C adds no migration/dependency/publication hook.
- `listings.search.forms.SearchForm(params)` binds an empty QueryDict too, calls the shared parser with original repeated values, and derives only catalog presentation controls in memory. Typed fields use dotted a.KEY.min/max/eq names. Blank named controls carry exact hidden source; tree/unselected forms emit none. Active numeric equality reopens as one equality control, without conflicting range controls. Options union canonical values from eligible same-type/unit compatible schemas, restricted to frozen refs on replay; false remains explicit.
- UI-only `category_apply=1` removes all a.*, schema/schema_version/schemas and page before parsing, preserves common criteria, and loads the selected category's controls. Ordinary GET search carries no page. Stale category/source gives visible validation, never reinterpretation. Recognized entered values are escaped and retained, including prior attribute values that no longer have controls.
- `views.index` performs form/parser -> matching -> ordering -> Paginator12. Invalid state has search_valid=False, search_spec=None, page_obj=None and no Listing SQL/COUNT. Successful state keeps selected_category as canonical ID string or empty legacy selection. Malformed legacy category remains unfiltered; valid missing positive category gives a legitimate empty result.
- Presentation-only bounded_page classifies huge numeric spellings before int: missing/nonnumeric first; nonpositive/out-of-range last. Pagination calls the canonical builder at most3 times (one budget reservation before Listing SQL plus previous/next), preserving normalized criteria/frozen refs once. Count, limited SQL rows and image prefetch remain bounded; listing rows are not matched/sorted in Python.
- Dedicated search_pagination.html uses precomputed previous_url/next_url; the existing owner/moderation listings/pagination.html is unchanged. Normal GET/no-JS browse is baseline; no search HTMX/history layer was added. Scoped search CSS retains shared branding/cards/public-photo routes.
- Stable rendered markers: #search-results for valid browse; “Bu ölçütlerle ilan bulunamadı.” for successful zero matches; #search-errors and “Arama ölçütlerini kontrol edin” for invalid criteria. `/?price_min=10` is a safe HTTP200 invalid-dependency probe.
- DEBUG-only search_browser_fixture accepts only a fresh16-hex run and Site.domain localhost:8089. It creates fresh reserved synthetic users with unusable passwords, a reviewer permission on the newly created reviewer only, category schemas/25published ties and generated synthetic media. It accepts no existing account IDs/credentials and touches no preexisting listing/account permissions. The driver uses disposable anonymous contexts and never saves auth state.

Current acceptance: final **255 full NEW tests /106.649s**, **21 C tests /10.690s**, preceding **117 affected tests /45.232s**, Django/migration checks PASS; actual **75 Chromium assertions** at390/1440px with JS-disabled GET/category apply/pagination/error/reset. Complete current evidence and limitations: `docs/SEARCH_VERIFICATION.md`. Historical Phase 1/A/B reports remain unchanged; no Git checkpoint or remote CI claim.

## Conversations — Phase3 domain and HTTP

Task A independently Spec PASS / Quality APPROVED. Canonical authority is Conversation.initiator_id / recipient_id, never arbitrary Participant membership or staff status. UUID Conversation links a listing and immutable canonical parties; subject captures only the first approved title. Message uses the persisted positive signed64 model PK for explicit through_message_id, a per-thread sequence and sender-scoped UUID client_token. Participant.last_read_sequence and archived_at are personal state; UserBlock is directional. New contact preference is Listing.contact_enabled with persistent database default. Independent moderation.MessagingRestriction does not change public visibility.

Public service signatures in conversations.services (all keyword-only):

- start_conversation(*, actor, listing_id, body, client_token) -> Message.
- send_message(*, actor, conversation_id, body, client_token) -> Message.
- mark_read(*, actor, conversation_id, through_message_id) -> Participant.
- set_archived(*, actor, conversation_id, archived) -> Participant.
- block_user(*, actor, other_user_id) -> UserBlock; unblock_user(*, actor, other_user_id).
- set_contact_enabled(*, actor, listing_id, enabled) -> Listing.

Queries in conversations.queries: inbox_conversations(*, actor, archived=False) -> SQL-ordered QuerySet; conversation_for_actor(*, actor, conversation_id) -> canonical Conversation; conversation_messages(*, actor, conversation_id) -> descending-sequence Message QuerySet; start_context(*, actor, listing_id) -> (Listing, existing Conversation|None). Inbox annotation names are viewer_last_read_sequence, viewer_archived_at, last_message_preview (SQL160 chars), has_unread. B slices12/30 rows before reversing only the displayed message group. can_reply(*, actor, conversation) is advisory; service permissions repeat under locks.

Message services own normalization: raw8000 cap, strict UTF-8, CRLF/CR -> LF, outer trim, nonblank/no NUL, normalized4000 code points. Same sender+token+normalized body returns the persisted original Message with no state mutation; changed body raises ValidationError(code=token_conflict). The HTTP form validates field presence/UUID and passes raw text to these public services. Bound errors map400; token conflict409 retains text and supplies a fresh hidden UUID. Active canonical authorization precedes replay; new replies deliberately ignore listing lifecycle/contact/public visibility but recheck both active accounts, blocks and messaging restrictions.

Namespaced conversations routes:

| Name | Method and route |
| --- | --- |
| inbox | GET /mesajlar/ (archived=1, page) |
| start | GET/POST /mesajlar/ilan/<listing_uuid>/ |
| contact | POST /mesajlar/ilan/<listing_uuid>/iletisim/ (enabled exactly0 or1) |
| detail | GET /mesajlar/<conversation_uuid>/ |
| history | GET /mesajlar/<conversation_uuid>/mesajlar/ (page, after_sequence) |
| send | POST /mesajlar/<conversation_uuid>/gonder/ |
| mark_read | POST /mesajlar/<conversation_uuid>/okundu/ (through_message_id) |
| archive / unarchive | POST /mesajlar/<conversation_uuid>/arsivle/ / arsivden-cikar/ |
| block / unblock | POST /mesajlar/<conversation_uuid>/engelle/ / engeli-kaldir/ |

Canonical thread lookup precedes pagination and metadata. Outside/missing thread404, known policy denial403, malformed form/watermark400. Pages are1..999999999, at most9 ASCII decimal chars; malformed/out-of-range404. Fixed named PRG targets ignore caller next/user IDs. Block target derives from the canonical other party. Valid private view responses, errors, fragments and PRG carry private,no-store and nosniff. Ordinary middleware CSRF remains enabled; GET never mutates state.

Newest history polling15s guards document visibility and history-control focus; composer remains outside the swap. Equal after_sequence returns204 only after canonical authorization; older pages carry no poll. GET/poll never advances read state. Read POST acknowledges the displayed message PK and is monotonic; a later insertion remains unread. New incoming messages clear only the recipient's archive.

The synthetic driver/command requires DEBUG, Site localhost:8089, independently inspected developer web/DB labels, exact source/volume/network/port bindings, developer media mount, current database and inspected/DNS DB address. Fresh16-hex runs only; reserved newly verified ordinary users, passwords in runner memory/stdin only, no real target IDs accepted. Fixture close/paginate operations resolve only their run's own main listing. Real UI evidence and final full-suite provenance: docs/CONVERSATIONS_VERIFICATION.md. Remote CI is not claimed executed.
