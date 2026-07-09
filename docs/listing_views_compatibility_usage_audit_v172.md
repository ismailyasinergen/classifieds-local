# v172 Listing Views Compatibility Usage / Dependency Audit

LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_V172

## Summary

- Views path: `listings/views.py`
- Views total lines: `157`
- Facade-only state: `True`
- Only approved compatibility re-exports remain: `True`
- Wildcard imports present: `False`
- Protected facade names: `37`
- Usage/dependency records found: `74`
- Names with detected compatibility usage: `('ListingCreateView', 'ListingDeleteView', 'ListingDetailView', 'ListingListView', 'ListingUpdateView', '_create_moderation_notice', 'active_approved_listings', 'apply_listing_filters', 'default_listing_expiry', 'listing_approve', 'listing_archive', 'listing_favorite_toggle', 'listing_feature_days_update', 'listing_feature_priority_update', 'listing_feature_toggle', 'listing_image_delete', 'listing_reject', 'listing_renew', 'listing_report_archive_listing', 'listing_report_create', 'listing_report_dismiss', 'listing_report_export_csv', 'listing_report_queue', 'listing_report_review', 'listing_report_suspend_listing', 'moderation_queue', 'my_listing_reports', 'save_uploaded_listing_images', 'saved_search_bulk_action', 'saved_search_create', 'saved_search_delete', 'saved_search_list', 'saved_search_notifications_toggle', 'saved_search_rename', 'validate_uploaded_images')`
- Names without detected usage: `('SidebarCategoriesMixin', '_safe_reporter_note')`
- Safe to remove any re-exports now: `False`

## Helper compatibility names with detected usage

- `_create_moderation_notice`
- `active_approved_listings`
- `apply_listing_filters`
- `default_listing_expiry`
- `save_uploaded_listing_images`
- `validate_uploaded_images`

## `*_views` compatibility names with detected usage

- `ListingCreateView`
- `ListingDeleteView`
- `ListingDetailView`
- `ListingListView`
- `ListingUpdateView`
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

## Usage records

- `ListingCreateView` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `ListingDeleteView` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `ListingDetailView` — `facade_attribute_usage` — `listings/test_browse_search_detail_contract_v156.py:101` — listing_views.ListingDetailView,
- `ListingDetailView` — `facade_attribute_usage` — `listings/test_browse_search_detail_contract_v156.py:117` — self.assertIs(getattr(match.func, "view_class", None), listing_views.ListingDetailView)
- `ListingDetailView` — `facade_attribute_usage` — `listings/test_browse_search_detail_contract_v156.py:230` — self.assertIs(getattr(match.func, "view_class", None), listing_views.ListingDetailView)
- `ListingDetailView` — `facade_attribute_usage` — `listings/test_browse_search_detail_view_extraction_v157.py:41` — listing_views.ListingDetailView,
- `ListingDetailView` — `facade_attribute_usage` — `listings/test_browse_search_detail_view_extraction_v157.py:51` — self.assertIs(view_class, listing_views.ListingDetailView)
- `ListingDetailView` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `ListingListView` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `ListingUpdateView` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `__facade_module__` — `facade_module_import` — `listings/test_browse_search_detail_contract_v156.py:28` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_browse_search_detail_view_extraction_v157.py:19` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_crud_uploads_contract_v160.py:23` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_crud_uploads_view_extraction_v161.py:20` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_favorite_view_extraction_v155.py:17` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_favorites_contract_v154.py:27` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_promotion_view_extraction_v152.py:16` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_promotions_contract_v151.py:27` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_reports_contract_v163.py:13` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_reports_view_extraction_v164.py:13` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_views_facade_consolidation_audit_v171.py:18` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_views_import_cleanup_contract_v169.py:12` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_views_import_cleanup_v170.py:18` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_listing_views_import_hygiene_audit_v168.py:12` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_post_extraction_listing_views_audit_v167.py:14` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_saved_searches_contract_v165.py:13` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_saved_searches_view_extraction_v166.py:13` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_uncategorized_lane_contract_v158.py:21` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/test_uncategorized_lane_view_extraction_v159.py:18` — from listings import views as listing_views
- `__facade_module__` — `facade_module_import` — `listings/urls.py:2` — from . import views as listing_views_v130
- `_create_moderation_notice` — `direct_from_listings_views_import` — `listings/test_listing_moderation_helper_extraction_v143.py:7` — from listings.views import _create_moderation_notice as views_create_moderation_notice
- `_create_moderation_notice` — `facade_attribute_usage` — `listings/test_listing_views_facade_consolidation_audit_v171.py:70` — self.assertIs(listing_views._create_moderation_notice, listing_moderation_helpers._create_moderation_notice)
- `_create_moderation_notice` — `facade_attribute_usage` — `listings/test_listing_views_import_cleanup_v170.py:71` — listing_views._create_moderation_notice,
- `active_approved_listings` — `facade_attribute_usage` — `listings/test_listing_views_facade_consolidation_audit_v171.py:72` — self.assertIs(listing_views.active_approved_listings, listing_visibility_helpers.active_approved_listings)
- `active_approved_listings` — `facade_attribute_usage` — `listings/test_listing_views_import_cleanup_v170.py:79` — listing_views.active_approved_listings,
- `active_approved_listings` — `direct_from_listings_views_import` — `listings/test_listing_visibility_helper_extraction_v146.py:7` — from listings.views import active_approved_listings as views_active_approved_listings
- `apply_listing_filters` — `direct_from_listings_views_import` — `listings/test_listing_filter_helper_extraction_v142.py:7` — from listings.views import apply_listing_filters as views_apply_listing_filters
- `apply_listing_filters` — `facade_attribute_usage` — `listings/test_listing_views_facade_consolidation_audit_v171.py:69` — self.assertIs(listing_views.apply_listing_filters, listing_filter_helpers.apply_listing_filters)
- `apply_listing_filters` — `facade_attribute_usage` — `listings/test_listing_views_import_cleanup_v170.py:69` — self.assertIs(listing_views.apply_listing_filters, listing_filter_helpers.apply_listing_filters)
- `default_listing_expiry` — `direct_from_listings_views_import` — `listings/test_listing_lifecycle_helper_extraction_v145.py:7` — from listings.views import default_listing_expiry as views_default_listing_expiry
- `default_listing_expiry` — `facade_attribute_usage` — `listings/test_listing_views_facade_consolidation_audit_v171.py:71` — self.assertIs(listing_views.default_listing_expiry, listing_lifecycle_helpers.default_listing_expiry)
- `default_listing_expiry` — `facade_attribute_usage` — `listings/test_listing_views_import_cleanup_v170.py:75` — listing_views.default_listing_expiry,
- `listing_approve` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_archive` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_favorite_toggle` — `facade_attribute_usage` — `listings/test_listing_favorite_view_extraction_v155.py:32` — listing_views.listing_favorite_toggle,
- `listing_favorite_toggle` — `facade_attribute_usage` — `listings/test_listing_favorite_view_extraction_v155.py:41` — self.assertIs(match.func, listing_views.listing_favorite_toggle)
- `listing_favorite_toggle` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_feature_days_update` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_feature_priority_update` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_feature_toggle` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_image_delete` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_reject` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_renew` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_archive_listing` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_create` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_dismiss` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_export_csv` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_queue` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_review` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `listing_report_suspend_listing` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `moderation_queue` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `my_listing_reports` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `save_uploaded_listing_images` — `direct_from_listings_views_import` — `listings/test_listing_image_helper_extraction_v147.py:7` — from listings.views import save_uploaded_listing_images as views_save_uploaded_listing_images
- `save_uploaded_listing_images` — `facade_attribute_usage` — `listings/test_listing_views_facade_consolidation_audit_v171.py:73` — self.assertIs(listing_views.save_uploaded_listing_images, listing_image_helpers.save_uploaded_listing_images)
- `save_uploaded_listing_images` — `facade_attribute_usage` — `listings/test_listing_views_import_cleanup_v170.py:83` — listing_views.save_uploaded_listing_images,
- `saved_search_bulk_action` — `facade_attribute_usage` — `listings/urls.py:74` — path("saved-searches/bulk/", listing_views_v130.saved_search_bulk_action, name="saved_search_bulk_action"),
- `saved_search_create` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `saved_search_delete` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `saved_search_list` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `saved_search_notifications_toggle` — `direct_from_listings_views_import` — `listings/urls.py:4` — from .views import (
- `saved_search_rename` — `facade_attribute_usage` — `listings/urls.py:75` — path("saved-searches/<int:pk>/rename/", listing_views_v130.saved_search_rename, name="saved_search_rename"),
- `validate_uploaded_images` — `direct_from_listings_views_import` — `listings/test_listing_image_validation_helper_extraction_v148.py:7` — from listings.views import validate_uploaded_images as views_validate_uploaded_images
- `validate_uploaded_images` — `facade_attribute_usage` — `listings/test_listing_views_facade_consolidation_audit_v171.py:74` — self.assertIs(listing_views.validate_uploaded_images, listing_image_helpers.validate_uploaded_images)
- `validate_uploaded_images` — `facade_attribute_usage` — `listings/test_listing_views_import_cleanup_v170.py:87` — listing_views.validate_uploaded_images,

## Recommendation

Do not remove helper compatibility re-exports or `*_views` re-export paths in v172.

A later implementation checkpoint may remove a compatibility name only after this audit reports no source, test, template, URL configuration, or route dependency for that name.

## Non-goals

- Do not move runtime code in v172.
- Do not remove helper compatibility re-exports in v172.
- Do not remove `*_views` compatibility re-export paths in v172.
- Do not change URLs, templates, permissions, models, migrations, or behavior.
