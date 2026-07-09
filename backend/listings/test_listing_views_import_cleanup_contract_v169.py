from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_import_cleanup_contract_v169 as contract
from listings import views as listing_views


SNAPSHOT_IMPORT_RECORDS_V169 = ({'bound_names': ('timedelta',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 1,
  'module': 'datetime',
  'original_names': ('timedelta',)},
 {'bound_names': ('Decimal', 'InvalidOperation'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 2,
  'module': 'decimal',
  'original_names': ('Decimal', 'InvalidOperation')},
 {'bound_names': ('Path',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 3,
  'module': 'pathlib',
  'original_names': ('Path',)},
 {'bound_names': ('messages',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 5,
  'module': 'django.contrib',
  'original_names': ('messages',)},
 {'bound_names': ('staff_member_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 6,
  'module': 'django.contrib.admin.views.decorators',
  'original_names': ('staff_member_required',)},
 {'bound_names': ('login_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 7,
  'module': 'django.contrib.auth.decorators',
  'original_names': ('login_required',)},
 {'bound_names': ('LoginRequiredMixin', 'UserPassesTestMixin'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 8,
  'module': 'django.contrib.auth.mixins',
  'original_names': ('LoginRequiredMixin', 'UserPassesTestMixin')},
 {'bound_names': ('Q',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 9,
  'module': 'django.db.models',
  'original_names': ('Q',)},
 {'bound_names': ('get_object_or_404', 'redirect', 'render'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 10,
  'module': 'django.shortcuts',
  'original_names': ('get_object_or_404', 'redirect', 'render')},
 {'bound_names': ('reverse_lazy',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 11,
  'module': 'django.urls',
  'original_names': ('reverse_lazy',)},
 {'bound_names': ('timezone',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 12,
  'module': 'django.utils',
  'original_names': ('timezone',)},
 {'bound_names': ('require_POST',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 13,
  'module': 'django.views.decorators.http',
  'original_names': ('require_POST',)},
 {'bound_names': ('CreateView', 'DeleteView', 'DetailView', 'ListView', 'UpdateView'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 14,
  'module': 'django.views.generic',
  'original_names': ('CreateView', 'DeleteView', 'DetailView', 'ListView', 'UpdateView')},
 {'bound_names': ('SellerStore',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 16,
  'module': 'accounts.models',
  'original_names': ('SellerStore',)},
 {'bound_names': ('Category',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 17,
  'module': 'categories.models',
  'original_names': ('Category',)},
 {'bound_names': ('ListingForm',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 19,
  'module': 'forms',
  'original_names': ('ListingForm',)},
 {'bound_names': ('Listing', 'ListingFavorite', 'ListingImage'),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 20,
  'module': 'models',
  'original_names': ('Listing', 'ListingFavorite', 'ListingImage')},
 {'bound_names': ('SidebarCategoriesMixin',
                  'ListingListView',
                  'listing_approve',
                  'listing_reject',
                  'listing_archive',
                  'listing_renew',
                  'listing_feature_toggle'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 22,
  'module': 'listing_uncategorized_views',
  'original_names': ('SidebarCategoriesMixin',
                     'ListingListView',
                     'listing_approve',
                     'listing_reject',
                     'listing_archive',
                     'listing_renew',
                     'listing_feature_toggle')},
 {'bound_names': ('ListingCreateView',
                  'ListingUpdateView',
                  'ListingDeleteView',
                  'listing_image_delete',
                  'listing_feature_days_update'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 32,
  'module': 'listing_crud_uploads_views',
  'original_names': ('ListingCreateView',
                     'ListingUpdateView',
                     'ListingDeleteView',
                     'listing_image_delete',
                     'listing_feature_days_update')},
 {'bound_names': ('moderation_queue',
                  'listing_report_create',
                  'listing_report_queue',
                  'listing_report_export_csv',
                  'my_listing_reports',
                  '_safe_reporter_note',
                  'listing_report_review',
                  'listing_report_dismiss',
                  'listing_report_suspend_listing',
                  'listing_report_archive_listing'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 61,
  'module': 'listing_reports_views',
  'original_names': ('moderation_queue',
                     'listing_report_create',
                     'listing_report_queue',
                     'listing_report_export_csv',
                     'my_listing_reports',
                     '_safe_reporter_note',
                     'listing_report_review',
                     'listing_report_dismiss',
                     'listing_report_suspend_listing',
                     'listing_report_archive_listing')},
 {'bound_names': ('listing_feature_priority_update',),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 77,
  'module': 'listing_promotion_views',
  'original_names': ('listing_feature_priority_update',)},
 {'bound_names': ('messages',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 105,
  'module': 'django.contrib',
  'original_names': ('messages',)},
 {'bound_names': ('staff_member_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 106,
  'module': 'django.contrib.admin.views.decorators',
  'original_names': ('staff_member_required',)},
 {'bound_names': ('login_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 107,
  'module': 'django.contrib.auth.decorators',
  'original_names': ('login_required',)},
 {'bound_names': ('Q',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 108,
  'module': 'django.db.models',
  'original_names': ('Q',)},
 {'bound_names': ('HttpResponse',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 109,
  'module': 'django.http',
  'original_names': ('HttpResponse',)},
 {'bound_names': ('get_object_or_404', 'redirect', 'render'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 110,
  'module': 'django.shortcuts',
  'original_names': ('get_object_or_404', 'redirect', 'render')},
 {'bound_names': ('require_POST',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 111,
  'module': 'django.views.decorators.http',
  'original_names': ('require_POST',)},
 {'bound_names': ('staff_member_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 150,
  'module': 'django.contrib.admin.views.decorators',
  'original_names': ('staff_member_required',)},
 {'bound_names': ('messages',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 151,
  'module': 'django.contrib',
  'original_names': ('messages',)},
 {'bound_names': ('get_object_or_404', 'redirect'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 152,
  'module': 'django.shortcuts',
  'original_names': ('get_object_or_404', 'redirect')},
 {'bound_names': ('require_POST',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 153,
  'module': 'django.views.decorators.http',
  'original_names': ('require_POST',)},
 {'bound_names': ('apply_listing_filters',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 154,
  'module': 'listing_filter_helpers',
  'original_names': ('apply_listing_filters',)},
 {'bound_names': ('_create_moderation_notice',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 155,
  'module': 'listing_moderation_helpers',
  'original_names': ('_create_moderation_notice',)},
 {'bound_names': ('default_listing_expiry',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 156,
  'module': 'listing_lifecycle_helpers',
  'original_names': ('default_listing_expiry',)},
 {'bound_names': ('active_approved_listings',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 157,
  'module': 'listing_visibility_helpers',
  'original_names': ('active_approved_listings',)},
 {'bound_names': ('save_uploaded_listing_images',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 158,
  'module': 'listing_image_helpers',
  'original_names': ('save_uploaded_listing_images',)},
 {'bound_names': ('validate_uploaded_images',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 159,
  'module': 'listing_image_helpers',
  'original_names': ('validate_uploaded_images',)},
 {'bound_names': ('listing_favorite_toggle',),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 160,
  'module': 'listing_favorite_views',
  'original_names': ('listing_favorite_toggle',)},
 {'bound_names': ('ListingDetailView',),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 161,
  'module': 'listing_browse_detail_views',
  'original_names': ('ListingDetailView',)},
 {'bound_names': ('saved_search_create',
                  'saved_search_list',
                  'saved_search_notifications_toggle',
                  'saved_search_delete',
                  'saved_search_bulk_action',
                  'saved_search_rename'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 180,
  'module': 'saved_searches_views',
  'original_names': ('saved_search_create',
                     'saved_search_list',
                     'saved_search_notifications_toggle',
                     'saved_search_delete',
                     'saved_search_bulk_action',
                     'saved_search_rename')})

SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_MODULES_V169 = ('listing_browse_detail_views',
 'listing_crud_uploads_views',
 'listing_favorite_views',
 'listing_promotion_views',
 'listing_reports_views',
 'listing_uncategorized_views',
 'saved_searches_views')

SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_NAMES_V169 = ('ListingCreateView',
 'ListingDeleteView',
 'ListingDetailView',
 'ListingListView',
 'ListingUpdateView',
 'SidebarCategoriesMixin',
 '_safe_reporter_note',
 'listing_approve',
 'listing_archive',
 'listing_favorite_toggle',
 'listing_feature_days_update',
 'listing_feature_priority_update',
 'listing_feature_toggle',
 'listing_image_delete',
 'listing_reject',
 'listing_renew',
 'listing_report_archive_listing',
 'listing_report_create',
 'listing_report_dismiss',
 'listing_report_export_csv',
 'listing_report_queue',
 'listing_report_review',
 'listing_report_suspend_listing',
 'moderation_queue',
 'my_listing_reports',
 'saved_search_bulk_action',
 'saved_search_create',
 'saved_search_delete',
 'saved_search_list',
 'saved_search_notifications_toggle',
 'saved_search_rename')

SNAPSHOT_NON_VIEW_IMPORT_MODULES_V169 = ('accounts.models',
 'categories.models',
 'datetime',
 'decimal',
 'django.contrib',
 'django.contrib.admin.views.decorators',
 'django.contrib.auth.decorators',
 'django.contrib.auth.mixins',
 'django.db.models',
 'django.http',
 'django.shortcuts',
 'django.urls',
 'django.utils',
 'django.views.decorators.http',
 'django.views.generic',
 'forms',
 'listing_filter_helpers',
 'listing_image_helpers',
 'listing_lifecycle_helpers',
 'listing_moderation_helpers',
 'listing_visibility_helpers',
 'models',
 'pathlib')

SNAPSHOT_NON_VIEW_IMPORT_BOUND_NAMES_V169 = ('Category',
 'CreateView',
 'Decimal',
 'DeleteView',
 'DetailView',
 'HttpResponse',
 'InvalidOperation',
 'ListView',
 'Listing',
 'ListingFavorite',
 'ListingForm',
 'ListingImage',
 'LoginRequiredMixin',
 'Path',
 'Q',
 'Q',
 'SellerStore',
 'UpdateView',
 'UserPassesTestMixin',
 '_create_moderation_notice',
 'active_approved_listings',
 'apply_listing_filters',
 'default_listing_expiry',
 'get_object_or_404',
 'get_object_or_404',
 'get_object_or_404',
 'login_required',
 'login_required',
 'messages',
 'messages',
 'messages',
 'redirect',
 'redirect',
 'redirect',
 'render',
 'render',
 'require_POST',
 'require_POST',
 'require_POST',
 'reverse_lazy',
 'save_uploaded_listing_images',
 'staff_member_required',
 'staff_member_required',
 'staff_member_required',
 'timedelta',
 'timezone',
 'validate_uploaded_images')

SNAPSHOT_DUPLICATE_BOUND_NAMES_V169 = ('Q', 'get_object_or_404', 'login_required', 'messages', 'redirect', 'render', 'require_POST', 'staff_member_required')

SNAPSHOT_WILDCARD_IMPORT_MODULES_V169 = ()


def _callbacks_by_route_name():
    callbacks: dict[str, list[object]] = defaultdict(list)

    def visit(patterns):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):
                if pattern.name:
                    callbacks[pattern.name].append(pattern.callback)
            elif isinstance(pattern, URLResolver):
                visit(pattern.url_patterns)

    visit(get_resolver().url_patterns)
    return callbacks


class ListingViewsImportCleanupContractV169Tests(SimpleTestCase):
    def test_v169_marker_is_declared(self):
        self.assertEqual(
            contract.LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_MARKER_V169,
            "LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_V169",
        )

    def test_v169_views_py_is_still_facade_only(self):
        report = contract.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.top_level_function_names, ())
        self.assertEqual(report.top_level_class_names, ())
        self.assertEqual(report.total_top_level_definitions, 0)
        self.assertTrue(report.is_facade_only)

    def test_v169_current_import_inventory_is_locked_before_cleanup(self):
        report = contract.build_report(Path("."))

        self.assertEqual(report.import_records, SNAPSHOT_IMPORT_RECORDS_V169)
        self.assertEqual(
            report.compatibility_view_reexport_modules,
            SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_MODULES_V169,
        )
        self.assertEqual(
            report.compatibility_view_reexport_names,
            SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_NAMES_V169,
        )
        self.assertEqual(report.non_view_import_modules, SNAPSHOT_NON_VIEW_IMPORT_MODULES_V169)
        self.assertEqual(report.non_view_import_bound_names, SNAPSHOT_NON_VIEW_IMPORT_BOUND_NAMES_V169)
        self.assertEqual(report.duplicate_bound_names, SNAPSHOT_DUPLICATE_BOUND_NAMES_V169)
        self.assertEqual(report.wildcard_import_modules, SNAPSHOT_WILDCARD_IMPORT_MODULES_V169)

    def test_v169_expected_compatibility_reexport_modules_are_present(self):
        report = contract.build_report(Path("."))

        self.assertEqual(report.missing_expected_reexport_modules, ())
        self.assertIn("listing_crud_uploads_views", report.compatibility_view_reexport_modules)
        self.assertIn("listing_reports_views", report.compatibility_view_reexport_modules)
        self.assertIn("saved_searches_views", report.compatibility_view_reexport_modules)

    def test_v169_facade_has_no_wildcard_imports(self):
        report = contract.build_report(Path("."))

        self.assertTrue(report.has_no_wildcard_imports)
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v169_public_url_callbacks_resolve_through_non_views_modules(self):
        callbacks_by_name = _callbacks_by_route_name()
        matched_route_names: list[str] = []

        for route_name, callbacks in callbacks_by_name.items():
            for callback in callbacks:
                callback_name = getattr(callback, "__name__", "")
                if not callback_name or not hasattr(listing_views, callback_name):
                    continue

                reexported_callback = getattr(listing_views, callback_name)
                if reexported_callback is not callback:
                    continue

                matched_route_names.append(route_name)

                self.assertNotEqual(
                    getattr(callback, "__module__", ""),
                    "listings.views",
                    f"{route_name} unexpectedly resolves to an object defined in listings.views",
                )

        self.assertIn("saved_search_list", matched_route_names)
        self.assertIn("report_queue", matched_route_names)

    def test_v169_markdown_documents_contract_and_non_goals(self):
        report = contract.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_import_cleanup_contract_v169.md"
            contract.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(contract.LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_MARKER_V169, text)
        self.assertIn("This is a contract checkpoint before any imports are removed", text)
        self.assertIn("Do not remove imports in v169", text)
        self.assertIn("Do not move runtime code in v169", text)
        self.assertIn("Compatibility view re-export modules protected", text)
        self.assertIn("Non-view bound names captured as cleanup candidates", text)
