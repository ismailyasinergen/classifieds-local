# v168 Listing Views Compatibility / Import Hygiene Audit

LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_V168

## Summary

- Views path: `listings/views.py`
- Views total lines: `187`
- Top-level functions/classes remaining: `0`
- Facade-only state: `True`
- Wildcard imports present: `False`
- Missing expected compatibility re-export modules: `()`

## Compatibility view re-export modules

- `listing_browse_detail_views`
- `listing_crud_uploads_views`
- `listing_favorite_views`
- `listing_promotion_views`
- `listing_reports_views`
- `listing_uncategorized_views`
- `saved_searches_views`

## Compatibility re-exported names

- `ListingCreateView`
- `ListingDeleteView`
- `ListingDetailView`
- `ListingListView`
- `ListingUpdateView`
- `SidebarCategoriesMixin`
- `_safe_reporter_note`
- `listing_approve`
- `listing_archive`
- `listing_favorite_toggle`
- `listing_feature_days_update`
- `listing_feature_priority_update`
- `listing_feature_toggle`
- `listing_image_delete`
- `listing_reject`
- `listing_renew`
- `listing_report_archive_listing`
- `listing_report_create`
- `listing_report_dismiss`
- `listing_report_export_csv`
- `listing_report_queue`
- `listing_report_review`
- `listing_report_suspend_listing`
- `moderation_queue`
- `my_listing_reports`
- `saved_search_bulk_action`
- `saved_search_create`
- `saved_search_delete`
- `saved_search_list`
- `saved_search_notifications_toggle`
- `saved_search_rename`

## Relative non-view import modules still present in facade

- `forms`
- `listing_filter_helpers`
- `listing_image_helpers`
- `listing_lifecycle_helpers`
- `listing_moderation_helpers`
- `listing_visibility_helpers`
- `models`

## Absolute import modules still present in facade

- `accounts.models`
- `categories.models`
- `datetime`
- `decimal`
- `django.contrib`
- `django.contrib.admin.views.decorators`
- `django.contrib.auth.decorators`
- `django.contrib.auth.mixins`
- `django.db.models`
- `django.http`
- `django.shortcuts`
- `django.urls`
- `django.utils`
- `django.views.decorators.http`
- `django.views.generic`
- `pathlib`

## Duplicate imported names

- `Q`
- `get_object_or_404`
- `login_required`
- `messages`
- `redirect`
- `render`
- `require_POST`
- `staff_member_required`

## Recommendation

Keep listings/views.py as a compatibility facade. Before removing any imports, add a dedicated compatibility/import cleanup contract and verify every public URL callback still resolves through listings.views.

## Non-goals

- Do not move runtime code in v168.
- Do not remove compatibility re-export paths in v168.
- Do not change URLs, templates, permissions, models, migrations, or behavior.
- Do not delete imports without a separate cleanup contract and route-resolution guard.
