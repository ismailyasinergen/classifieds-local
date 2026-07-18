# Notification Delivery Preferences (v288)

v288 adds an authenticated **Notification preferences** page at
`/accounts/notification-preferences/`. Users can independently enable listing
price-alert email, saved-search new-listing email, and saved-search price-drop
email. All fields default to enabled, and a missing preference row is also
treated as enabled so existing users keep the pre-v288 behavior.

The global saved-search preference and the existing per-search
`email_notifications_enabled` switch use AND semantics. Delivery code checks
the relevant type preference before claiming a v287 event. A disabled logical
event is stored as terminal `skipped` with the non-sensitive category
`preference_disabled`, zero send attempts, and no sent timestamp. This prevents
retry storms and means re-enabling a preference does not release a stale
backlog. A later listing or price transition has a new event identity and can
be delivered normally. Saved-search suppression also advances the activity
watermark after the current candidate identities are recorded.

Preference lookups are batched for command and batch-sender paths. No
per-listing or per-alert preference query is introduced. The settings form is
server-rendered, authenticated, CSRF-protected, scoped to `request.user`, and
uses explicit labels and help text. Staff can inspect preference rows through a
read-only admin view; no public event or preference API was added.

Migration `0021_notification_delivery_preference_v288` is additive and depends
on v287 migration `0020`. There is no destructive backfill or new dependency.
The application has no verified-email state, provider bounce webhook, or
delivery-retention policy; those operational concerns remain documented in the
technical recommendations rather than being guessed in this feature.
