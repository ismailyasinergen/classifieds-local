# Saved search notification operations

Saved-search email notifications are operator-triggered. The project does not enable automatic background sending by itself.

## Dry-run preview

Run dry-run first. It previews candidates and does not send email.

```bash
docker exec classifieds_web python manage.py check_saved_search_notifications \
  --stale-before-hours 24 \
  --max-searches 100 \
  --site-base-url https://classifieds.local
```

## Explicit send

Only send after the dry-run output looks safe.

```bash
docker exec classifieds_web python manage.py check_saved_search_notifications \
  --send \
  --stale-before-hours 24 \
  --max-searches 100 \
  --site-base-url https://classifieds.local
```

## Cron-style example

Do not install this blindly. Confirm email backend settings, sender identity, and the production site URL first.

```cron
# Preview every hour; no email is sent.
0 * * * * cd /app && python manage.py check_saved_search_notifications --stale-before-hours 24 --max-searches 100 --site-base-url https://classifieds.local

# Explicit sending example; enable only after dry-run verification.
# 15 * * * * cd /app && python manage.py check_saved_search_notifications --send --stale-before-hours 24 --max-searches 100 --site-base-url https://classifieds.local
```

## Operational notes

- --send is required before any notification email is sent.
- Zero-match saved searches are skipped without timestamp updates.
- Saved searches whose user has no email address are skipped safely.
- --stale-before-hours limits processing to searches that have never been checked or were checked before the cutoff.
- --max-searches caps the number of enabled saved searches processed per run.

## Failure observability

The send command isolates delivery failures per saved search.

- If one saved-search email send fails, later saved searches in the same batch continue.
- Failed sends are counted as `email failure(s)` in the final summary.
- Failed saved-search IDs are printed as `Failed saved search ID(s): ...`.
- Failed sends do not update `last_notification_checked_at` or `last_notification_sent_at`.
- Successful sends in the same batch still update notification timestamps.

## Admin guidance

The SavedSearch admin shows lightweight notification status fields:

- `Notification status` summarizes disabled alerts, missing recipients, last checked, or last sent state.
- `User email` shows the delivery recipient or `(no email)`.
- `Query preview` helps operators identify what the saved search will run.
- `Notification run guidance` reminds operators that sending is manual, dry-run-first, and failure-isolated.

## Troubleshooting send failures

When the command reports `email failure(s)`:

1. Copy the failed saved-search IDs from the command output.
2. Inspect those saved searches in Django admin.
3. Confirm the user has a valid email address.
4. Confirm production email backend credentials and sender settings.
5. Re-run a dry-run for the failed saved-search IDs before trying `--send` again.

Example retry for one failed saved search:

```bash
docker exec classifieds_web python manage.py check_saved_search_notifications --saved-search-id 123 --site-base-url https://classifieds.local
```

Send only after the retry dry-run looks safe:

```bash
docker exec classifieds_web python manage.py check_saved_search_notifications --saved-search-id 123 --send --site-base-url https://classifieds.local
```

<!-- SAVED_SEARCH_NOTIFICATION_RUNBOOK_ADMIN_POLISH_V86 -->
