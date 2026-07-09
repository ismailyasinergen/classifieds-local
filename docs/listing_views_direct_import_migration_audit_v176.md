# v176 Listing Views Direct Import Migration Audit

LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_V176

## Summary

- Views path: `listings/views.py`
- Views total lines: `155`
- Protected remaining facade names: `35`
- Migration records: `54`
- Migration names: `('ListingCreateView', 'ListingDeleteView', 'ListingDetailView', 'ListingListView', 'ListingUpdateView', '_create_moderation_notice', 'active_approved_listings', 'apply_listing_filters', 'default_listing_expiry', 'listing_approve', 'listing_archive', 'listing_favorite_toggle', 'listing_feature_days_update', 'listing_feature_priority_update', 'listing_feature_toggle', 'listing_image_delete', 'listing_reject', 'listing_renew', 'listing_report_archive_listing', 'listing_report_create', 'listing_report_dismiss', 'listing_report_export_csv', 'listing_report_queue', 'listing_report_review', 'listing_report_suspend_listing', 'moderation_queue', 'my_listing_reports', 'save_uploaded_listing_images', 'saved_search_bulk_action', 'saved_search_create', 'saved_search_delete', 'saved_search_list', 'saved_search_notifications_toggle', 'saved_search_rename', 'validate_uploaded_images')`
- Names without migration records: `()`
- All remaining names have migration paths: `True`
- Source modules with migrations: `('listing_browse_detail_views', 'listing_crud_uploads_views', 'listing_favorite_views', 'listing_filter_helpers', 'listing_image_helpers', 'listing_lifecycle_helpers', 'listing_moderation_helpers', 'listing_promotion_views', 'listing_reports_views', 'listing_uncategorized_views', 'listing_visibility_helpers', 'saved_searches_views')`
- Migration count by source module: `(('listing_browse_detail_views', 6), ('listing_crud_uploads_views', 5), ('listing_favorite_views', 3), ('listing_filter_helpers', 3), ('listing_image_helpers', 6), ('listing_lifecycle_helpers', 3), ('listing_moderation_helpers', 3), ('listing_promotion_views', 1), ('listing_reports_views', 9), ('listing_uncategorized_views', 6), ('listing_visibility_helpers', 3), ('saved_searches_views', 6))`
- Migration count by usage form: `(('direct_from_listings_views_import', 33), ('facade_attribute_usage', 21))`
- Manual review records: `0`
- v174 targeted removal preserved: `True`
- Removed-v174 names still present: `()`
- Removed-v174 names absent: `('SidebarCategoriesMixin', '_safe_reporter_note')`
- Facade-only state: `True`
- Import hygiene: `True`
- Safe to change imports in v176: `False`

## Migration records

- `listings/test_browse_search_detail_contract_v156.py:101` — `ListingDetailView` — `facade_attribute_usage` → `from listings.listing_browse_detail_views import ListingDetailView` — listing_views.ListingDetailView,
- `listings/test_browse_search_detail_contract_v156.py:117` — `ListingDetailView` — `facade_attribute_usage` → `from listings.listing_browse_detail_views import ListingDetailView` — self.assertIs(getattr(match.func, "view_class", None), listing_views.ListingDetailView)
- `listings/test_browse_search_detail_contract_v156.py:230` — `ListingDetailView` — `facade_attribute_usage` → `from listings.listing_browse_detail_views import ListingDetailView` — self.assertIs(getattr(match.func, "view_class", None), listing_views.ListingDetailView)
- `listings/test_browse_search_detail_view_extraction_v157.py:41` — `ListingDetailView` — `facade_attribute_usage` → `from listings.listing_browse_detail_views import ListingDetailView` — listing_views.ListingDetailView,
- `listings/test_browse_search_detail_view_extraction_v157.py:51` — `ListingDetailView` — `facade_attribute_usage` → `from listings.listing_browse_detail_views import ListingDetailView` — self.assertIs(view_class, listing_views.ListingDetailView)
- `listings/test_listing_favorite_view_extraction_v155.py:32` — `listing_favorite_toggle` — `facade_attribute_usage` → `from listings.listing_favorite_views import listing_favorite_toggle` — listing_views.listing_favorite_toggle,
- `listings/test_listing_favorite_view_extraction_v155.py:41` — `listing_favorite_toggle` — `facade_attribute_usage` → `from listings.listing_favorite_views import listing_favorite_toggle` — self.assertIs(match.func, listing_views.listing_favorite_toggle)
- `listings/test_listing_filter_helper_extraction_v142.py:7` — `apply_listing_filters` — `direct_from_listings_views_import` → `from listings.listing_filter_helpers import apply_listing_filters` — from listings.views import apply_listing_filters as views_apply_listing_filters
- `listings/test_listing_image_helper_extraction_v147.py:7` — `save_uploaded_listing_images` — `direct_from_listings_views_import` → `from listings.listing_image_helpers import save_uploaded_listing_images` — from listings.views import save_uploaded_listing_images as views_save_uploaded_listing_images
- `listings/test_listing_image_validation_helper_extraction_v148.py:7` — `validate_uploaded_images` — `direct_from_listings_views_import` → `from listings.listing_image_helpers import validate_uploaded_images` — from listings.views import validate_uploaded_images as views_validate_uploaded_images
- `listings/test_listing_lifecycle_helper_extraction_v145.py:7` — `default_listing_expiry` — `direct_from_listings_views_import` → `from listings.listing_lifecycle_helpers import default_listing_expiry` — from listings.views import default_listing_expiry as views_default_listing_expiry
- `listings/test_listing_moderation_helper_extraction_v143.py:7` — `_create_moderation_notice` — `direct_from_listings_views_import` → `from listings.listing_moderation_helpers import _create_moderation_notice` — from listings.views import _create_moderation_notice as views_create_moderation_notice
- `listings/test_listing_views_facade_consolidation_audit_v171.py:69` — `apply_listing_filters` — `facade_attribute_usage` → `from listings.listing_filter_helpers import apply_listing_filters` — self.assertIs(listing_views.apply_listing_filters, listing_filter_helpers.apply_listing_filters)
- `listings/test_listing_views_facade_consolidation_audit_v171.py:70` — `_create_moderation_notice` — `facade_attribute_usage` → `from listings.listing_moderation_helpers import _create_moderation_notice` — self.assertIs(listing_views._create_moderation_notice, listing_moderation_helpers._create_moderation_notice)
- `listings/test_listing_views_facade_consolidation_audit_v171.py:71` — `default_listing_expiry` — `facade_attribute_usage` → `from listings.listing_lifecycle_helpers import default_listing_expiry` — self.assertIs(listing_views.default_listing_expiry, listing_lifecycle_helpers.default_listing_expiry)
- `listings/test_listing_views_facade_consolidation_audit_v171.py:72` — `active_approved_listings` — `facade_attribute_usage` → `from listings.listing_visibility_helpers import active_approved_listings` — self.assertIs(listing_views.active_approved_listings, listing_visibility_helpers.active_approved_listings)
- `listings/test_listing_views_facade_consolidation_audit_v171.py:73` — `save_uploaded_listing_images` — `facade_attribute_usage` → `from listings.listing_image_helpers import save_uploaded_listing_images` — self.assertIs(listing_views.save_uploaded_listing_images, listing_image_helpers.save_uploaded_listing_images)
- `listings/test_listing_views_facade_consolidation_audit_v171.py:74` — `validate_uploaded_images` — `facade_attribute_usage` → `from listings.listing_image_helpers import validate_uploaded_images` — self.assertIs(listing_views.validate_uploaded_images, listing_image_helpers.validate_uploaded_images)
- `listings/test_listing_views_import_cleanup_v170.py:75` — `apply_listing_filters` — `facade_attribute_usage` → `from listings.listing_filter_helpers import apply_listing_filters` — self.assertIs(listing_views.apply_listing_filters, listing_filter_helpers.apply_listing_filters)
- `listings/test_listing_views_import_cleanup_v170.py:77` — `_create_moderation_notice` — `facade_attribute_usage` → `from listings.listing_moderation_helpers import _create_moderation_notice` — listing_views._create_moderation_notice,
- `listings/test_listing_views_import_cleanup_v170.py:81` — `default_listing_expiry` — `facade_attribute_usage` → `from listings.listing_lifecycle_helpers import default_listing_expiry` — listing_views.default_listing_expiry,
- `listings/test_listing_views_import_cleanup_v170.py:85` — `active_approved_listings` — `facade_attribute_usage` → `from listings.listing_visibility_helpers import active_approved_listings` — listing_views.active_approved_listings,
- `listings/test_listing_views_import_cleanup_v170.py:89` — `save_uploaded_listing_images` — `facade_attribute_usage` → `from listings.listing_image_helpers import save_uploaded_listing_images` — listing_views.save_uploaded_listing_images,
- `listings/test_listing_views_import_cleanup_v170.py:93` — `validate_uploaded_images` — `facade_attribute_usage` → `from listings.listing_image_helpers import validate_uploaded_images` — listing_views.validate_uploaded_images,
- `listings/test_listing_visibility_helper_extraction_v146.py:7` — `active_approved_listings` — `direct_from_listings_views_import` → `from listings.listing_visibility_helpers import active_approved_listings` — from listings.views import active_approved_listings as views_active_approved_listings
- `listings/urls.py:4` — `ListingCreateView` — `direct_from_listings_views_import` → `from listings.listing_crud_uploads_views import ListingCreateView` — from .views import (
- `listings/urls.py:4` — `ListingDeleteView` — `direct_from_listings_views_import` → `from listings.listing_crud_uploads_views import ListingDeleteView` — from .views import (
- `listings/urls.py:4` — `ListingDetailView` — `direct_from_listings_views_import` → `from listings.listing_browse_detail_views import ListingDetailView` — from .views import (
- `listings/urls.py:4` — `ListingListView` — `direct_from_listings_views_import` → `from listings.listing_uncategorized_views import ListingListView` — from .views import (
- `listings/urls.py:4` — `ListingUpdateView` — `direct_from_listings_views_import` → `from listings.listing_crud_uploads_views import ListingUpdateView` — from .views import (
- `listings/urls.py:4` — `listing_approve` — `direct_from_listings_views_import` → `from listings.listing_uncategorized_views import listing_approve` — from .views import (
- `listings/urls.py:4` — `listing_archive` — `direct_from_listings_views_import` → `from listings.listing_uncategorized_views import listing_archive` — from .views import (
- `listings/urls.py:4` — `listing_favorite_toggle` — `direct_from_listings_views_import` → `from listings.listing_favorite_views import listing_favorite_toggle` — from .views import (
- `listings/urls.py:4` — `listing_feature_days_update` — `direct_from_listings_views_import` → `from listings.listing_crud_uploads_views import listing_feature_days_update` — from .views import (
- `listings/urls.py:4` — `listing_feature_priority_update` — `direct_from_listings_views_import` → `from listings.listing_promotion_views import listing_feature_priority_update` — from .views import (
- `listings/urls.py:4` — `listing_feature_toggle` — `direct_from_listings_views_import` → `from listings.listing_uncategorized_views import listing_feature_toggle` — from .views import (
- `listings/urls.py:4` — `listing_image_delete` — `direct_from_listings_views_import` → `from listings.listing_crud_uploads_views import listing_image_delete` — from .views import (
- `listings/urls.py:4` — `listing_reject` — `direct_from_listings_views_import` → `from listings.listing_uncategorized_views import listing_reject` — from .views import (
- `listings/urls.py:4` — `listing_renew` — `direct_from_listings_views_import` → `from listings.listing_uncategorized_views import listing_renew` — from .views import (
- `listings/urls.py:4` — `listing_report_archive_listing` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_archive_listing` — from .views import (
- `listings/urls.py:4` — `listing_report_create` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_create` — from .views import (
- `listings/urls.py:4` — `listing_report_dismiss` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_dismiss` — from .views import (
- `listings/urls.py:4` — `listing_report_export_csv` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_export_csv` — from .views import (
- `listings/urls.py:4` — `listing_report_queue` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_queue` — from .views import (
- `listings/urls.py:4` — `listing_report_review` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_review` — from .views import (
- `listings/urls.py:4` — `listing_report_suspend_listing` — `direct_from_listings_views_import` → `from listings.listing_reports_views import listing_report_suspend_listing` — from .views import (
- `listings/urls.py:4` — `moderation_queue` — `direct_from_listings_views_import` → `from listings.listing_reports_views import moderation_queue` — from .views import (
- `listings/urls.py:4` — `my_listing_reports` — `direct_from_listings_views_import` → `from listings.listing_reports_views import my_listing_reports` — from .views import (
- `listings/urls.py:4` — `saved_search_create` — `direct_from_listings_views_import` → `from listings.saved_searches_views import saved_search_create` — from .views import (
- `listings/urls.py:4` — `saved_search_delete` — `direct_from_listings_views_import` → `from listings.saved_searches_views import saved_search_delete` — from .views import (
- `listings/urls.py:4` — `saved_search_list` — `direct_from_listings_views_import` → `from listings.saved_searches_views import saved_search_list` — from .views import (
- `listings/urls.py:4` — `saved_search_notifications_toggle` — `direct_from_listings_views_import` → `from listings.saved_searches_views import saved_search_notifications_toggle` — from .views import (
- `listings/urls.py:74` — `saved_search_bulk_action` — `facade_attribute_usage` → `from listings.saved_searches_views import saved_search_bulk_action` — path("saved-searches/bulk/", listing_views_v130.saved_search_bulk_action, name="saved_search_bulk_action"),
- `listings/urls.py:75` — `saved_search_rename` — `facade_attribute_usage` → `from listings.saved_searches_views import saved_search_rename` — path("saved-searches/<int:pk>/rename/", listing_views_v130.saved_search_rename, name="saved_search_rename"),

## Manual review records

No manual review records detected.

## Guardrails

- v176 is audit-only.
- Do not change imports in v176.
- Do not edit `backend/listings/views.py` in v176.
- Do not remove any remaining facade re-export in v176.
- A later checkpoint may migrate one small import group after this audit is reviewed.
