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
