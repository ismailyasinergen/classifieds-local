# Conversations developer verification

2026-10-09; native developer worktree ws_9c012facba, classifieds-rebuild-dev, http://localhost:8089. Task A's independently approved22 files are unchanged. This is developer acceptance; independent B/whole-package review and original-runtime release remain controller-owned. No Git checkpoint or remote CI execution is claimed.

## Product acceptance

23 HTTP regression tests exercise ordinary login return, first-send PRG, replies, owner/self/outside/staff/injected Participant boundaries, malformed and foreign IDs, every mutation's GET/CSRF rejection, body4000/4001/raw8000/NUL/blank/CR normalization,4000 astral characters, malformed and reused/conflicting UUID token, escaped full pages/fragments/previews/bound errors and no private emails, private response headers, read/archival/block state isolation, disabled new contact and closed listing continuation. Real PostgreSQL13-thread/31-message pagination asserts SQL limits12/30, chronology, UUID ties, retained archive parameters and bounded query counts.

Captured GREEN:74 conversations tests (23 B HTTP plus51 Task A),9.899s;29 HTTP+moderation messaging tests2.960s, then3.212s after the form was simplified to pass raw text only to public mutation services. The final complete NEW suite uses the frozen source and parallel2; its full captured output, count and duration are retained in phase3/task-B-report.md.

## Genuine browser evidence

Run5a74455a59c44750: **PASS,128 assertions**, installed Playwright1.63.0 / Chromium153.0.8010.12. Actual ordinary verified synthetic logins, first-send keyboard activation, seller unread inbox/reply,15s newest-history refresh preserving composer, real history-focus poll suppression, explicit displayed watermark preserving a later incoming unread message, personal archive/unarchive, owned directional block/unblock, bound400 validation,4000 astral UI acceptance, SQL12/30 pagination, owner contact preference, closed-listing reply/new-initiator denial,1440x1000 desktop and390x844 mobile labels/focus/no overflow, mobile keyboard submit, and JS-disabled actual pointer send/read/GET refresh/older navigation completed. No unexpected page errors or request failures. No programmatic form submission or request shortcut was used.

Current bounded JSON: rebuild/test-artifacts/conversations/5a74455a59c44750/summary.json. Four genuine PNGs in the same run directory: desktop-conversation.png, mobile-composer.png, mobile-conversation.png, nojs-history.png. This final run followed the public-service-only form refactor, focused HTTP29 check and developer-web-only recreation; it exercised the final runtime source.

## Isolation and reproducibility

Use only the developer worktree, existing installed browser and these commands:

```bash
node rebuild/browser-tests/conversations.cjs
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test conversations moderation.tests.test_messaging --noinput --verbosity 1
docker compose -f rebuild/compose.yaml -f rebuild/compose.dev.yaml -p classifieds-rebuild-dev exec -T web python manage.py test --parallel 2 --noinput --verbosity 1
```

The runner verifies exact developer Compose service labels,8089-only port, read-only worktree bind, media/PostgreSQL volumes and shared developer network before any fixture/browser operation. The command additionally checks DEBUG, Site.domain localhost:8089, developer media mount, PostgreSQL current database and server address against both independently inspected DB IP and DNS. Fresh reserved16-hex run identities prevent reuse. It creates newly verified synthetic ordinary users only, passwords randomized and held exclusively in runner memory/stdin. Controlled close/paginate operations accept no listing/account IDs and touch only their own run rows. No real accounts/auth stores/cookies, Bridge configuration or original runtime were read or modified.

Before browser acceptance, only developer web was recreated with --no-build --no-deps --pull never --force-recreate --wait; developer DB/Redis and volumes stayed intact. Tests and browser do not run concurrently. Full suite uses parallel2 inside its one normal Django invocation because native Bridge transport times out around120s regardless shell timeout. A timeout without captured results is uncounted.

## Attempts and limitations

- Initial HTTP RED:23 tests,1.464s;21 missing conversations-namespace errors and one missing contact-CTA assertion failure; one absent-route test already passed.
- First implementation run:23 tests,3.461s; two errors from a service dictionary ValidationError used in a field cleaner. Form-wide cleaning fixed it; later removed redundant private-helper validation so public services remain authoritative.
- One misnamed moderation test-label attempt failed import and parallel traceback pickling; no dependency installed. Correct moderation.tests.test_messaging label passed.
- Browser7780814071af0431: stopped at10 guard checks before fixture writes because PostgreSQL inet text included/32. Independent SQL/DNS read found that cause; host(inet_server_addr()) now compares the exact host.
- Browser4f987931c1c0f537:118 successful assertions, then noJS long-page pointer stability timeout under smooth motion; its summary and three screenshots remain historical failed-attempt artifacts.
- Browserd075a6599b389b3e and5f8994dedca770c6:15 checks each then second-login DOMContentLoaded timeout. Server logs showed HTTP200 document/CSS and deferred HTMX only completing at timeout. Current harness uses normal allauth next=/mesajlar/ to avoid unrelated homepage lazy-image traffic and closes completed contexts; all contexts request reduced motion. No product behavior was bypassed.
- Subsequent run5bda0df8d11eb1a9 completed128 checks; final same-source refresh5a74455a59c44750 also completed128 checks including real noJS pointer controls. Historical partial/failed runs are not counted as additional acceptance passes.

The CI change only adds conversations.cjs and this document to the existing complete-source manifest array; backend discovery remains dynamic. No literal source-count assertion existed to change. Actual candidate manifest identity is reconciled in the task report. Remote CI, legacy suite, original migrations/transfer and public deployment are NOT RUN in Task B.

## Final frozen suite

The complete returned output, count, duration, checks/drift/whitespace results and exact candidate hashes are recorded in [phase3/task-B-report.md](phase3/task-B-report.md). No overlapping tests, migrations or source edits are permitted during that run.
