# Search verification — SearchSpec v1 and Turkish browse

2026-10-09; native Windows worktree ws_9c012facba. Development source/DB/browser evidence only. The independently reviewed A/B implementations are consumed unchanged by Task C. Local active acceptance is a separate root gate, recorded when executed in [search-release-report.md](phase2/search-release-report.md). Commits=none; HEAD remains3c0b949bef3636ab15780a4d8bf8a7e07f41a0ba.

## Actual gates

| Gate | Result |
| --- | --- |
| Initial18 rendered HTTP tests before UI | RED,10.097s:4failures/27error subcases; two image setup errors are fixture defects, not feature RED |
| Corrected two image fixture cases before UI |1expected missing-next_url RED,1existing query-bound PASS;1.236s |
| Initial browse implementation |18tests GREEN,11.206s |
| Prior-category entered-value retention | Focused1test RED0.655s -> GREEN0.699s |
| Combined A/B/C and affected prior UI/public visibility |117tests PASS,45.232s |
| Pre-final numeric-equality source |254full NEW tests PASS,104.381s; superseded by final gate below |
| Canonical numeric equality replay | Focused1test RED0.700s; final C module21tests GREEN10.690s |
| Pre-range-fix full NEW suite |255tests PASS,106.649s; historical C acceptance |
| Option-backed numeric range preservation |3focused tests: RED14subcases/3.319s -> GREEN2.840s; ordinary numeric option equality remained compatible |
| **Final full NEW suite after range fix** | **258tests PASS,68.712s**, --parallel 2 |
| System check | No issues |
| makemigrations --check --dry-run | No changes detected |
| migrate --check | Exit0; developer search migration already applied |
| Tracked diff whitespace | PASS; complete manifest/owned-source checks recorded in C report |
| **Actual focused Chromium acceptance** | **75assertions PASS**, real1440x1000 and390x844, JavaScript-disabled context,25tied rows,0page errors/0unexpected request failures |

The full suite's “Media enqueue unavailable ... pending scan will retry” message is an expected fallback exercised by an existing test, followed by OK. No legacy suite, old full seller/reviewer browser journey, unchanged checker-fixture tests, remote CI or release image test ran as part of C.

## Reproduce the new-app gates

Run from the development worktree root. All Django commands target the independent developer web container:

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test catalog.tests.test_search listings.tests.test_search_spec listings.tests.test_search_queries listings.tests.test_search_browse listings.tests.test_ui_contracts listings.tests.test_public_visibility --verbosity 1
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py check
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py makemigrations --check --dry-run
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py migrate --check
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test --parallel 2 --noinput --verbosity 1
```

The combined117-test run preceded the numeric-equality and three option-range regressions; that same targeted command now discovers121tests. The historical255 full/C21 gates include numeric equality, while the final258 full gate also includes all three option-range tests. No separate24-test C rerun is claimed. Exact reported counts belong to their actual executions.

Gunicorn has no autoreload. After final UI source, developer web alone was restarted with both Compose files/project name, then /health/ returned {status:ok}. No dependency, database/Redis restart or active-original mutation was needed for browser acceptance.

```bash
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev restart web
curl --fail --silent --show-error http://localhost:8089/health/
"C:\Program Files\nodejs\node.exe" rebuild/browser-tests/search.cjs
```

The exact installed driver is rebuild/.browser-test-tools/node_modules/playwright-core1.63.0; Chromium headless shell is C:\Users\ismai\AppData\Local\ms-playwright\chromium_headless_shell-1243\chrome-headless-shell-win64\chrome-headless-shell.exe, actual browser153.0.8010.12. These local tools are ignored test tooling, not a CI/browser installation promise.

## Real browser evidence

Final recorded browser run: **5e4c89a39abf9c1f**, before the narrowly scoped option-range fix. Its ordinary numeric/string/boolean fixture controls are unchanged by that fix; the new option-range branch is covered by the actual HTTP regressions below. Screenshots are unedited viewport PNGs of synthetic anonymous product screens. The driver reserves fresh category/query scope, creates25fresh equal-date/price published rows and uses no existing account/profile/session/storageState.

| File under rebuild/test-artifacts/search/5e4c89a39abf9c1f/ | Pixels | Bytes | SHA-256 |
| --- | --- | --- | --- |
| desktop-results.png |1440x1000 |52728 |b9d8d353c6f2950c998c53b88f13996b5edcd6229458144d24b7d9e3a93ef51b |
| mobile-filters.png |390x844 |27165 |55cf1437e5b8f64c63344105917431b51046ff3fa2b023f6a811d17a2b013aee |
| mobile-results.png |390x844 |44322 |e68504a7cd46d2564af464ddd756f740cd7676e8890a49b3afc53daa037c8103 |

summary.json contains the actual75-assertion result, versions, viewport sizes and screenshot hashes. All generated artifacts stay in the ignored test-artifacts path; no cookies, HAR, auth trace or account-settings screenshot is written.

Acceptance covered real native GET filter submission; Turkish labels; current approved derivative; compatible older options; explicit-false field omission; canonical decimal/currency/false and frozen schema refs; exactly one page; nonoverlapping stable12-row pages; back restoration; new search page reset; active numeric equality reopen/resubmit; mobile one-column/no document overflow/keyboard focus; stale category error; explicit category apply clearing old identity while retaining common criteria; legitimate empty results; JS-disabled GET search, pagination, tree apply, linked dependency error and unfiltered reset.

The JS-disabled form assertions use native keyboard button activation; its pagination/reset links use pointer activation. Desktop/mobile form pointer activation also passed. No claim is made that the final run validated JS-disabled pointer form activation. Disposable contexts request reduced motion for deterministic scrolling/capture and are closed after their phase to stop surplus lazy-image requests; product CSS remains unchanged.

Earlier exploratory browser attempts failed on exact-label colon handling, an image readiness race and no-JS navigation/activation timing. The label suffix now matches the visible Turkish labels; the driver awaits loaded image pixels, uses explicit keyboard activation for no-JS, bounded30/45second waits and closes completed contexts. The earlier failed runs and earlier70-assertion pass remain superseded historical artifacts, not final acceptance evidence.

## Contracts and limitations

Invalid criteria render HTTP200 with #search-errors, “Arama ölçütlerini kontrol edin” and page_obj=None. No listing SQL/count occurs, including for dependencies, duplicates, invalid typed controls and NUL. Valid browse renders #search-results; zero matches says “Bu ölçütlerle ilan bulunamadı.”. A safe invalid probe is /?price_min=10.

Legacy malformedcategory remains unfiltered; valid nonexistentpositiveID remains a zero-result category selection. Any three ASCII currency letters normalize uppercase; TRY/EUR/USD are suggestions. Tree/unselected forms render no named attributes. Exact controls carry hidden source identity, while active canonical predicates carry frozen targets. Kategoriyi uygula clears all a.*, schema/schema_version/schemas/page and preserves common criteria.

Matching/order remain SQL through the reviewed APIs; Paginator12 uses COUNT/LIMIT and current-image prefetch. Tests compare1vs25rows and require at most2Listing statements, no page overlap and deterministic descending UUID ties. Canonical builders are called at most3 times per request, not per listing/chip; maximum-page spelling is reserved before Listing SQL to prevent over-budget pagination URLs.

No throughput benchmark or index-performance promise follows from these small fixtures. Concurrent publication can change pages; this is stable ordering, not a result snapshot. No typo correction, Turkish stemming, cross-currency conversion, saved-search UI, messaging, external email delivery, data migration or public deployment is claimed.

C owns README ADP-M1 correction, current INTERFACES, this document and only a minimal CI manifest-list extension for search.cjs, compose.dev.yaml, LOCAL_SETUP/INTERFACES/SEARCH_VERIFICATION. The existing workflow shape and tests are unchanged; remote CI **NOT RUN**. Complete exact diff/snapshots and native source integrity are indexed in phase2/search-task-C-source-index.json with the implementation report at phase2/search-task-C-report.md. Phase1 reports remain historical.

## Final option-range regression correction

Root C-RANGE-1 confirmed that option-backed integer/decimal fields rendered only equality even when a canonical search carried active min/max predicates. Six real HTTP replay subcases broadened the returned set; eight invalid-input subcases omitted the entered range control. The dedicated three-test RED completed with14failures/3.319s, then the same three tests passed/2.840s after the minimum forms.py correction. Ordinary option equality dropdown behavior already passed before the fix and remains covered.

The form now renders active range controls on numeric option fields, including one-sided and zero endpoints. Conflicting entered equality/range values remain visible with the validation error until corrected; invalid resubmission does not silently discard the conflict. Canonical schema refs, matching sets and entered values are asserted through rendered HTTP GET replay. Shared parser, query, index and migration source is unchanged.

A first post-fix serial full-suite request returned MCP -32603 request-timeout without a test result; it is not counted as PASS. A read-only process check confirmed that invocation had ended before retry. The exact complete258-test suite then passed with two Django test workers in68.712s. Test databases/clones were created and destroyed by the test runner; no active-original database was used. System check, migration dry-run and tracked whitespace gates also passed. The source diff/snapshots and review references are in phase2/search-task-C-fix1-report.md.
