# v144 Remaining Listing View Extraction Audit

Marker: `REMAINING_LISTING_VIEW_EXTRACTION_AUDIT_V144`

## Target

- Path: `C:\Users\ismai\Desktop\classifieds_local\backend\listings\views.py`
- Exists: `True`
- Total lines: `2362`
- Top-level functions: `52`
- Top-level classes: `9`
- View-like functions: `48`
- Helper candidates: `4`
- Low-risk candidates: `4`
- Medium-risk candidates: `0`

## v141 candidate exhaustion check

- Extracted v141 candidates expected missing: `apply_listing_filters, _create_moderation_notice`
- Extracted v141 candidates missing count: `2`
- Extracted v141 candidates still present: `none`

## Recommended next candidate

- Name: `default_listing_expiry`
- Lines: `2`
- Risk: `low`
- Category: `non_view_helper`
- Reason: non-view helper under 80 lines

## Remaining candidates

| Name | Lines | Risk | Category | First arg | Reason |
|---|---:|---|---|---|---|
| `default_listing_expiry` | 2 | low | non_view_helper | `` | non-view helper under 80 lines |
| `active_approved_listings` | 6 | low | non_view_helper | `queryset` | non-view helper under 80 lines |
| `save_uploaded_listing_images` | 11 | low | non_view_helper | `listing` | non-view helper under 80 lines |
| `validate_uploaded_images` | 19 | low | non_view_helper | `uploaded_files` | non-view helper under 80 lines |

## v144 rules

- Do not re-extract `apply_listing_filters`; it was completed in v142.
- Do not re-extract `_create_moderation_notice`; it was completed in v143.
- Prefer low-risk non-view helpers before any request-first function view.
- Do not change behavior in this audit checkpoint.
- Use the audit result to choose the next extraction checkpoint.
