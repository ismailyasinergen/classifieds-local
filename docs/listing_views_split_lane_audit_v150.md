# v150 Listing Views Split-Lane Audit

LISTING_VIEWS_SPLIT_LANE_AUDIT_V150

## Purpose

After v148, low-risk helper extraction candidates in `backend/listings/views.py` are exhausted.
After v149, the project-wide audit still identifies `backend/listings/views.py` as the largest active product-code refactor target.
v150 maps the remaining top-level definitions into split lanes before any behavior-bearing code is moved.

## Non-goals

- Do not move view functions or classes.
- Do not change URL routing.
- Do not change imports.
- Do not change templates, models, migrations, permissions, forms, or behavior.

## Summary

- Root: `C:\Users\ismai\Desktop\classifieds_local`
- Target: `C:\Users\ismai\Desktop\classifieds_local\backend\listings\views.py`
- Exists: True
- Total lines: 2328
- Top-level functions: 48
- Top-level classes: 9
- Total top-level definitions: 57

## Recommended next lane

- Lane: `listing_promotions`
- Definitions: 1
- Total lines: 20
- High-risk definitions: 0
- Medium-risk definitions: 0
- Low-risk definitions: 1
- Request-first functions: 1
- Split readiness: `candidate_for_first_split`

## Lane summary

| Lane | Definitions | Lines | High | Medium | Low | Request-first | Split readiness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| saved_search | 6 | 526 | 1 | 0 | 5 | 6 | needs_contract_tests_first |
| favorites | 1 | 23 | 0 | 0 | 1 | 1 | candidate_for_first_split |
| listing_promotions | 1 | 20 | 0 | 0 | 1 | 1 | candidate_for_first_split |
| listing_reports_moderation | 33 | 1173 | 0 | 10 | 23 | 33 | too_large_split_in_sub_lanes |
| listing_crud_uploads | 8 | 158 | 0 | 0 | 8 | 3 | candidate_for_first_split |
| seller_listing_management | 0 | 0 | 0 | 0 | 0 | 0 | empty |
| browse_search_detail | 1 | 48 | 0 | 0 | 1 | 0 | candidate_for_first_split |
| uncategorized | 7 | 100 | 0 | 0 | 7 | 4 | candidate_for_first_split |

## Definition details

| Lane | Name | Kind | Lines | Line count | Risk | Request first |
| --- | --- | --- | --- | ---: | --- | --- |
| saved_search | `saved_search_create` | function | 1787-1814 | 28 | low | True |
| saved_search | `saved_search_list` | function | 1818-2175 | 358 | high | True |
| saved_search | `saved_search_notifications_toggle` | function | 2180-2215 | 36 | low | True |
| saved_search | `saved_search_delete` | function | 2220-2226 | 7 | low | True |
| saved_search | `saved_search_bulk_action` | function | 2229-2277 | 49 | low | True |
| saved_search | `saved_search_rename` | function | 2280-2327 | 48 | low | True |
| favorites | `listing_favorite_toggle` | function | 289-311 | 23 | low | True |
| listing_promotions | `listing_feature_priority_update` | function | 433-452 | 20 | low | True |
| listing_reports_moderation | `moderation_queue` | function | 250-266 | 17 | low | True |
| listing_reports_moderation | `moderation_queue` | function | 379-427 | 49 | low | True |
| listing_reports_moderation | `listing_report_create` | function | 482-529 | 48 | low | True |
| listing_reports_moderation | `listing_report_queue` | function | 533-571 | 39 | low | True |
| listing_reports_moderation | `listing_report_review` | function | 576-587 | 12 | low | True |
| listing_reports_moderation | `listing_report_dismiss` | function | 592-603 | 12 | low | True |
| listing_reports_moderation | `listing_report_archive_listing` | function | 608-626 | 19 | low | True |
| listing_reports_moderation | `listing_report_queue` | function | 631-697 | 67 | medium | True |
| listing_reports_moderation | `listing_report_export_csv` | function | 702-788 | 87 | medium | True |
| listing_reports_moderation | `listing_report_create` | function | 793-850 | 58 | medium | True |
| listing_reports_moderation | `my_listing_reports` | function | 854-871 | 18 | low | True |
| listing_reports_moderation | `listing_report_create` | function | 875-928 | 54 | medium | True |
| listing_reports_moderation | `my_listing_reports` | function | 932-949 | 18 | low | True |
| listing_reports_moderation | `listing_report_queue` | function | 953-1013 | 61 | medium | True |
| listing_reports_moderation | `_safe_reporter_note` | function | 1026-1027 | 2 | low | True |
| listing_reports_moderation | `listing_report_create` | function | 1031-1084 | 54 | medium | True |
| listing_reports_moderation | `my_listing_reports` | function | 1088-1105 | 18 | low | True |
| listing_reports_moderation | `listing_report_queue` | function | 1109-1188 | 80 | medium | True |
| listing_reports_moderation | `listing_report_export_csv` | function | 1192-1277 | 86 | medium | True |
| listing_reports_moderation | `listing_report_suspend_listing` | function | 1282-1301 | 20 | low | True |
| listing_reports_moderation | `listing_report_review` | function | 1306-1322 | 17 | low | True |
| listing_reports_moderation | `listing_report_dismiss` | function | 1327-1343 | 17 | low | True |
| listing_reports_moderation | `listing_report_archive_listing` | function | 1348-1368 | 21 | low | True |
| listing_reports_moderation | `listing_report_review` | function | 1404-1427 | 24 | low | True |
| listing_reports_moderation | `listing_report_dismiss` | function | 1432-1455 | 24 | low | True |
| listing_reports_moderation | `listing_report_suspend_listing` | function | 1460-1497 | 38 | low | True |
| listing_reports_moderation | `listing_report_archive_listing` | function | 1502-1540 | 39 | low | True |
| listing_reports_moderation | `listing_report_suspend_listing` | function | 1558-1618 | 61 | medium | True |
| listing_reports_moderation | `listing_report_archive_listing` | function | 1623-1683 | 61 | medium | True |
| listing_reports_moderation | `listing_report_review` | function | 1715-1727 | 13 | low | True |
| listing_reports_moderation | `listing_report_dismiss` | function | 1733-1745 | 13 | low | True |
| listing_reports_moderation | `listing_report_suspend_listing` | function | 1751-1763 | 13 | low | True |
| listing_reports_moderation | `listing_report_archive_listing` | function | 1769-1781 | 13 | low | True |
| listing_crud_uploads | `ListingCreateView` | class | 137-169 | 33 | low | False |
| listing_crud_uploads | `ListingUpdateView` | class | 172-211 | 40 | low | False |
| listing_crud_uploads | `ListingDeleteView` | class | 214-228 | 15 | low | False |
| listing_crud_uploads | `listing_image_delete` | function | 233-246 | 14 | low | True |
| listing_crud_uploads | `listing_renew` | function | 333-345 | 13 | low | True |
| listing_crud_uploads | `listing_feature_days_update` | function | 458-478 | 21 | low | True |
| listing_crud_uploads | `ListingCreateView` | class | 1372-1382 | 11 | low | False |
| listing_crud_uploads | `ListingUpdateView` | class | 1386-1396 | 11 | low | False |
| browse_search_detail | `ListingDetailView` | class | 87-134 | 48 | low | False |
| uncategorized | `SidebarCategoriesMixin` | class | 52-63 | 12 | low | False |
| uncategorized | `ListingListView` | class | 66-84 | 19 | low | False |
| uncategorized | `listing_approve` | function | 271-275 | 5 | low | True |
| uncategorized | `listing_reject` | function | 280-284 | 5 | low | True |
| uncategorized | `listing_archive` | function | 317-328 | 12 | low | True |
| uncategorized | `listing_feature_toggle` | function | 351-374 | 24 | low | True |
| uncategorized | `ListingListView` | class | 1687-1709 | 23 | low | False |

## Safe sequencing rule

Before moving a lane into a new module, create or confirm focused tests for that lane and keep URL names, permission behavior, templates, redirects, querystrings, messages, and pagination unchanged.
