# v242 — Saved-Search Notification Production Delivery Implementation

Marker:

`V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION`

v242 modifies exactly five files:

1. `backend/config/settings.py`
2. `backend/listings/saved_search_notification_email_sender.py`
3. `backend/listings/management/commands/process_saved_search_notifications.py`
4. `backend/listings/test_saved_search_notification_production_delivery_implementation_v242.py`
5. `docs/saved_search_notification_production_delivery_implementation_v242.md`

Production delivery is default-off through:

`SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED`

Production execution requires:

- `--execute-production-send`
- `--confirm-production-delivery`
- one positive `--owner-id`
- an explicit `--limit` between 1 and 25
- a configured backend that is not locmem, dummy, console or file-based

The existing matcher, audited sender, persistent audit runtime and timestamp
rollback protections are reused.

Failed or refused delivery does not advance
`last_notification_sent_at`.

No model, migration, admin, URL, template, background worker, cron integration
or automatic scheduler delivery is introduced.

Next checkpoint:

v243: saved-search notification production delivery closeout audit
