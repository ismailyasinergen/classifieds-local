# v165 Saved Searches Contract Checkpoint

SAVED_SEARCHES_CONTRACT_V165

## Purpose

This checkpoint protects the remaining `saved_searches` lane before any runtime code is moved out of `backend/listings/views.py`.

After v164 extracted `listing_reports`, the v162 remaining-views audit recommends `saved_searches` as the next extraction lane.

## Scope

v165 is a contract checkpoint only.

It records and protects:

- the six saved-search callbacks currently local to `views.py`,
- the active source footprint for each callback,
- URL resolver identity for the current saved-search routes,
- current callback identity through `listings.views`,
- existing saved-search runtime test coverage.

## Protected saved-search callbacks

- `saved_search_create`: `28` lines, lines `181`-`208`
- `saved_search_list`: `358` lines, lines `212`-`569`
- `saved_search_notifications_toggle`: `36` lines, lines `574`-`609`
- `saved_search_delete`: `7` lines, lines `614`-`620`
- `saved_search_bulk_action`: `49` lines, lines `623`-`671`
- `saved_search_rename`: `48` lines, lines `674`-`721`

Total saved-search lane footprint: `526` lines.

## Protected route behavior

Saved-search route aliases are protected through Django's URL resolver.

Each protected callback must have at least one URL route resolving to the current `listings.views.<callback>` object:

- `saved_search_create`
- `saved_search_list`
- `saved_search_notifications_toggle`
- `saved_search_delete`
- `saved_search_bulk_action`
- `saved_search_rename`

## Existing saved-search test files

- `backend/listings/test_saved_search_bulk_actions.py`
- `backend/listings/test_saved_search_bulk_ui_polish.py`
- `backend/listings/test_saved_search_management_hardening.py`
- `backend/listings/test_saved_search_management_ui_polish.py`
- `backend/listings/test_saved_search_notification_admin_action_runbook_alignment.py`
- `backend/listings/test_saved_search_notification_admin_actions.py`
- `backend/listings/test_saved_search_notification_admin_changelist_smoke.py`
- `backend/listings/test_saved_search_notification_admin_list_polish.py`
- `backend/listings/test_saved_search_notification_matcher.py`
- `backend/listings/test_saved_search_notification_observability.py`
- `backend/listings/test_saved_search_notification_operator_ux.py`
- `backend/listings/test_saved_search_notification_runbook_admin_polish.py`
- `backend/listings/test_saved_search_notification_runbook_command_alignment.py`
- `backend/listings/test_saved_search_notification_scheduling_admin.py`
- `backend/listings/test_saved_search_notifications_foundation.py`
- `backend/listings/test_saved_search_rename_accessibility_polish.py`
- `backend/listings/test_saved_search_rename_edit_flow.py`
- `backend/listings/test_saved_search_rename_error_feedback.py`
- `backend/listings/test_saved_search_rename_inline_state_cleanup.py`
- `backend/listings/test_saved_search_rename_inline_toggle.py`
- `backend/listings/test_saved_search_rename_ux_polish.py`
- `backend/listings/test_saved_search_rename_visual_feedback.py`
- `backend/listings/test_saved_search_seller_store_email_alert_guardrails.py`
- `backend/listings/test_saved_search_seller_store_management_polish.py`
- `backend/listings/test_saved_search_tab_count_polish.py`
- `backend/listings/test_saved_search_type_filter_tabs.py`
- `backend/listings/test_saved_search_ux_polish.py`
- `backend/listings/test_saved_searches.py`

## Non-goals

- Do not move runtime code in v165.
- Do not create `saved_searches_views.py` in v165.
- Do not change URLs, permissions, templates, models, migrations, or runtime behavior.
- Do not remove compatibility access through `listings.views`.

## Next safe step

v166 should extract the protected saved-search lane into a dedicated module while preserving route callbacks and compatibility re-exports.
