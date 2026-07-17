# v273 — Public Browse Category Navigation UX Repair

## Checkpoint identity

- Base: `project-checkpoint-v272-recently-viewed-listings`
- Target:
  `project-checkpoint-v273-public-browse-category-navigation-ux-repair`
- Marker:
  `PUBLIC_BROWSE_CATEGORY_NAVIGATION_UX_REPAIR_V273`

## User-visible problem

The public listings page displayed the complete marketplace category taxonomy
before the listing search and results.

The same taxonomy was also visible in the global left sidebar.

This caused:

- A very tall first page
- Listing results being pushed far below the fold
- Duplicate category navigation
- An internal v186 marker being shown to visitors
- Poor scanning on desktop and mobile

## Exact scope

v273 changes exactly:

1. `backend/templates/categories/_category_navigation_v186.html`
2. `backend/listings/templates/listings/listing_list.html`
3. `backend/categories/test_public_browse_category_navigation_ux_repair_v273.py`
4. `docs/public_browse_category_navigation_ux_repair_v273.md`

## Compact disclosure behavior

When no category is selected:

- The category browser starts collapsed.
- Visitors see a compact “Browse by category” control.
- Listing search and results remain near the top of the page.

When a category is selected:

- The category browser starts open.
- The selected root branch opens.
- The selected child branch opens.
- Unrelated branches remain collapsed.
- The selected category receives `aria-current="page"`.

## Duplicate navigation repair

On the public listings browse page:

- The global expanded category sidebar is hidden.
- The main content expands to a single column.
- The compact category browser becomes the single visible category navigation.

Other pages retain the existing global sidebar behavior.

## Internal marker repair

The v186 marker remains in the rendered DOM for backward-compatible automated
tests but is hidden with `display: none`.

It is no longer visible to users and is removed from the accessibility tree by
the browser's `display: none` behavior.

## Compatibility

v273 preserves:

- v186 category URL generation
- Category descendant filtering
- Search query preservation
- Sort preservation
- Page-number removal when switching categories
- v187 public-browse mount
- v190 visual accessibility
- v191 saved-search category state
- v193 keyboard focus behavior
- Clear-category behavior

## Runtime boundary

v273 does not modify:

- Category models
- Listing models
- Views
- URLs
- Settings
- Sessions
- Recently viewed listings
- Similar listings
- Saved-search notification delivery
- Database schema
- Migrations

Migration `0017` remains absent.

## Manual QA

After the checkpoint:

1. Open `/listings/`.
2. Confirm the left category sidebar is not visible on this page.
3. Confirm “Browse by category” starts collapsed.
4. Confirm search controls and listings appear near the top.
5. Open the category browser.
6. Select a child or grandchild category.
7. Confirm only the selected category path is expanded.
8. Confirm the selected category is indicated.
9. Confirm “Clear category” removes only the category filter.
10. Confirm the internal v186 marker is not visible.
11. Confirm mobile layout remains usable.

## Next project action

After browser QA, return to the next concrete marketplace feature rather than
starting another category-navigation audit chain.
