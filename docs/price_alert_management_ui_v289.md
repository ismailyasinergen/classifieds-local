# Price-Alert Management UI (v289)

v289 adds an authenticated management page at `/listings/price-alerts/` for
listing-specific subscriptions created by v285. The page is linked from the
account menu, dashboard, and v288 notification-preference settings.

Alerts are ordered by creation time and primary key descending and paginated at
20 rows. One `select_related` query supplies listing and category data, and one
preference lookup supplies the global listing-alert email state; rendering does
not issue per-alert queries. Public, unexpired listings show their title, link,
category, location, subscription price, current price, and last-delivery time.
Non-public or expired listings use a generic unavailable state and do not expose
their current title, link, category, location, or price.

Removal is an authenticated, CSRF-protected POST scoped to `request.user`.
Unlike the public listing-detail toggle, it can remove an owned subscription
after the listing becomes unavailable. There is no staff override and no public
delivery-event endpoint. The UI does not expose event keys, attempts, recipient
details, or other v287 audit state.

The v288 global preference and subscription existence remain separate. Turning
email off keeps alerts visible and stored; the page explains the disabled state
and links back to notification preferences. A missing preference row retains
the existing enabled default.

No model or migration is added. Verified-recipient enforcement and delivery
event retention remain deferred until their product and privacy policies are
defined.
