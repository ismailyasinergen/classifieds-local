# v173 Listing Views Targeted Removal Contract

LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_V173

## Purpose

v173 freezes the exact two-name candidate pair discovered by the v172 checkpoint before v173 test/doc references existed.

v173 does not remove either candidate.

## Candidate names

- `SidebarCategoriesMixin`
- `_safe_reporter_note`

## Summary

- Views path: `listings/views.py`
- Views total lines: `157`
- Facade-only state: `True`
- Only approved compatibility re-exports remain: `True`
- Wildcard imports present: `False`
- Candidate names present in facade: `('SidebarCategoriesMixin', '_safe_reporter_note')`
- Candidate names missing from facade: `()`
- Target facade dependency records: `0`
- Informational plain target reference records: `41`
- Eligible for future targeted removal checkpoint: `True`
- Safe to remove in v173: `False`

## Candidate source modules

- `SidebarCategoriesMixin` from `listing_uncategorized_views`
- `_safe_reporter_note` from `listing_reports_views`

## Target facade dependency records

No target facade dependency records detected.

## Informational plain target reference records

- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_browse_detail_views.py:39` — class SidebarCategoriesMixin:
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_browse_detail_views.py:53` — class ListingDetailView(SidebarCategoriesMixin, DetailView):
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_crud_uploads_views.py:25` — SidebarCategoriesMixin,
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_crud_uploads_views.py:118` — class ListingCreateView(LoginRequiredMixin, SidebarCategoriesMixin, CreateView):
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_crud_uploads_views.py:152` — class ListingUpdateView(LoginRequiredMixin, UserPassesTestMixin, SidebarCategoriesMixin, UpdateView):
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_crud_uploads_views.py:197` — class ListingDeleteView(LoginRequiredMixin, UserPassesTestMixin, SidebarCategoriesMixin, DeleteView):
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_uncategorized_views.py:39` — "SidebarCategoriesMixin",
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_uncategorized_views.py:68` — class SidebarCategoriesMixin:
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_uncategorized_views.py:81` — class ListingListView(SidebarCategoriesMixin, ListView):
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_contract_v169.py:132` — {'bound_names': ('SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_contract_v169.py:144` — 'original_names': ('SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_contract_v169.py:362` — 'SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_v170.py:37` — 'SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/listing_views_split_lane_followup_audit_v153.py:40` — "view": 'SidebarCategoriesMixin, ListingListView, listing_approve, listing_reject, listing_archive, listing_renew, listing_feature_toggle',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_browse_search_detail_view_extraction_v157.py:34` — self.assertIn("SidebarCategoriesMixin", source)
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_listing_views_import_cleanup_contract_v169.py:134` — {'bound_names': ('SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_listing_views_import_cleanup_contract_v169.py:146` — 'original_names': ('SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_listing_views_import_cleanup_contract_v169.py:364` — 'SidebarCategoriesMixin',
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_uncategorized_lane_contract_v158.py:32` — "SidebarCategoriesMixin",
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_uncategorized_lane_view_extraction_v159.py:23` — "SidebarCategoriesMixin",
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_uncategorized_lane_view_extraction_v159.py:137` — if isinstance(base, ast.Name) and base.id == "SidebarCategoriesMixin":
- `SidebarCategoriesMixin` — `informational_plain_target_reference` — `listings/test_uncategorized_lane_view_extraction_v159.py:151` — self.assertIn("SidebarCategoriesMixin", exported_names)
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_reports_views.py:624` — def _safe_reporter_note(request, default):
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_reports_views.py:891` — report.reporter_note = _safe_reporter_note(
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_reports_views.py:912` — report.reporter_note = _safe_reporter_note(
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_reports_views.py:933` — report.reporter_note = _safe_reporter_note(
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_reports_views.py:958` — report.reporter_note = _safe_reporter_note(
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_contract_v169.py:171` — '_safe_reporter_note',
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_contract_v169.py:186` — '_safe_reporter_note',
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_contract_v169.py:363` — '_safe_reporter_note',
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/listing_views_import_cleanup_v170.py:38` — '_safe_reporter_note',
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/remaining_listing_views_post_v161_audit.py:100` — or item.name == "_safe_reporter_note"
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_reports_contract_v163.py:27` — "_safe_reporter_note": 1,
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_reports_contract_v163.py:37` — "_safe_reporter_note": 2,
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_reports_contract_v163.py:198` — "_safe_reporter_note",
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_reports_view_extraction_v164.py:24` — "_safe_reporter_note",
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_reports_view_extraction_v164.py:40` — "_safe_reporter_note": 1,
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_reports_view_extraction_v164.py:50` — "_safe_reporter_note": 2,
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_views_import_cleanup_contract_v169.py:173` — '_safe_reporter_note',
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_views_import_cleanup_contract_v169.py:188` — '_safe_reporter_note',
- `_safe_reporter_note` — `informational_plain_target_reference` — `listings/test_listing_views_import_cleanup_contract_v169.py:365` — '_safe_reporter_note',

## Guardrails

- Do not remove `SidebarCategoriesMixin` or `_safe_reporter_note` in v173.
- Plain references are informational only; facade dependency records are the blocker for removing names from `listings.views`.
- The candidate pair is frozen from the v172 checkpoint result; live v172 scans after adding v173 files are expected to see v173's own references.
- Do not remove helper compatibility re-exports in v173.
- Do not remove route/view compatibility re-export paths in v173.
- Do not change URLs, templates, permissions, models, migrations, or behavior.
- A later checkpoint may remove only these two names from `listings.views` if this contract remains green.
