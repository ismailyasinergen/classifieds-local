# Notification Delivery Deduplication (v287)

v287 adds a private `NotificationDeliveryEvent` ledger for listing price-drop,
saved-search new-listing, and saved-search price-drop email events. A SHA-256
event key is derived from a versioned logical identity: notification type,
recipient, listing, subscription or saved search, and price transition where
applicable. The database enforces uniqueness; random attempt IDs are never the
sole deduplication mechanism.

Candidate identities are inserted in bulk and claimed with one conditional
database update. A batch claim sets a private token, `processing` status, and
increments the attempt count. Email is sent outside the transaction. A short
completion update marks claimed rows `sent`; exceptions or zero-delivery results
become retryable `failed` rows. Retries are capped at five attempts. Processing
claims older than 15 minutes may be recovered. Missing recipients are recorded
as terminal `skipped` events, never as sent.

The ledger gives exactly-once logical event claiming under concurrent workers
and permanently suppresses sent events. External email itself is practically
deduplicated, not mathematically exactly once: a process crash after the email
provider accepts a message but before the completion update can cause one retry
after the stale-claim window. Provider idempotency would be required to close
that window.

Saved-search events are per result. A later valid reduction has a different
price-transition identity and can notify again; an increase does not qualify.
Unsubscribing removes future listing-alert candidates while prior ledger rows
remain for staff audit. Batch transition lookup and event claiming are bounded
queries with no per-result history fetch. Staff receive read-only admin
visibility; no public event endpoint or email body content is stored.

Migration `0020_notification_delivery_event_v287` is additive and follows
`0019_listingpricealert`.
