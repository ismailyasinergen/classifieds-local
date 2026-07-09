# v169 Listing Views Import Cleanup Contract

LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_V169

## Purpose

v169 is a contract checkpoint before any imports are removed from `backend/listings/views.py`.

It records the current facade/import surface after v168 and protects compatibility before a future cleanup implementation checkpoint.

## Current facade state

- `backend/listings/views.py` top-level functions/classes: `0`
- Compatibility view re-export modules: `('listing_browse_detail_views', 'listing_crud_uploads_views', 'listing_favorite_views', 'listing_promotion_views', 'listing_reports_views', 'listing_uncategorized_views', 'saved_searches_views')`
- Wildcard imports: `()`
- Duplicate bound import names: `('Q', 'get_object_or_404', 'login_required', 'messages', 'redirect', 'render', 'require_POST', 'staff_member_required')`

## Protected compatibility view re-export modules

- `listing_browse_detail_views`
- `listing_crud_uploads_views`
- `listing_favorite_views`
- `listing_promotion_views`
- `listing_reports_views`
- `listing_uncategorized_views`
- `saved_searches_views`

## Protected compatibility view re-export names

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

## Non-view import modules captured as cleanup candidates

These are captured for a future cleanup checkpoint. v169 does not remove them.

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
- `forms`
- `listing_filter_helpers`
- `listing_image_helpers`
- `listing_lifecycle_helpers`
- `listing_moderation_helpers`
- `listing_visibility_helpers`
- `models`
- `pathlib`

## Non-view bound names captured as cleanup candidates

These are captured for a future cleanup checkpoint. v169 does not remove them.

- `Category`
- `CreateView`
- `Decimal`
- `DeleteView`
- `DetailView`
- `HttpResponse`
- `InvalidOperation`
- `ListView`
- `Listing`
- `ListingFavorite`
- `ListingForm`
- `ListingImage`
- `LoginRequiredMixin`
- `Path`
- `Q`
- `Q`
- `SellerStore`
- `UpdateView`
- `UserPassesTestMixin`
- `_create_moderation_notice`
- `active_approved_listings`
- `apply_listing_filters`
- `default_listing_expiry`
- `get_object_or_404`
- `get_object_or_404`
- `get_object_or_404`
- `login_required`
- `login_required`
- `messages`
- `messages`
- `messages`
- `redirect`
- `redirect`
- `redirect`
- `render`
- `render`
- `require_POST`
- `require_POST`
- `require_POST`
- `reverse_lazy`
- `save_uploaded_listing_images`
- `staff_member_required`
- `staff_member_required`
- `staff_member_required`
- `timedelta`
- `timezone`
- `validate_uploaded_images`

## Guardrails

- Do not remove imports in v169.
- Do not move runtime code in v169.
- Do not change URLs, templates, permissions, models, migrations, or behavior.
- Before removing non-view imports, create a cleanup implementation checkpoint that preserves all public URL callback identities.
- Keep `listings.views` compatibility re-exports unless a later contract explicitly proves they are safe to remove.

## Next safe step

A later checkpoint may remove only proven non-view facade imports, while preserving route callback identity and `listings.views` compatibility re-exports.
## v170 follow-up

v170 implemented this contract by removing only proven non-view facade imports from `backend/listings/views.py` while preserving all compatibility `*_views` re-exports and public URL callback identities.
