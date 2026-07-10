from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_TRANSITION_CATEGORY_TAXONOMY_READINESS_MARKER_V181 = (
    "PROJECT_TRANSITION_CATEGORY_TAXONOMY_READINESS_V181"
)

RECOMMENDED_NEXT_FEATURE_AREA_V181 = "category_taxonomy"
RECOMMENDED_NEXT_CHECKPOINT_V181 = "v182-category-hierarchy-model-admin-safeguards"

CATEGORY_MODEL_PATH_CANDIDATES_V181 = (
    "categories/models.py",
    "backend/categories/models.py",
)

LISTING_MODEL_PATH_CANDIDATES_V181 = (
    "listings/models.py",
    "backend/listings/models.py",
)

LISTING_FORMS_PATH_CANDIDATES_V181 = (
    "listings/forms.py",
    "backend/listings/forms.py",
)

LISTING_URLS_PATH_CANDIDATES_V181 = (
    "listings/urls.py",
    "backend/listings/urls.py",
)

LISTING_BROWSE_SOURCE_PATH_CANDIDATES_V181 = (
    "listings/listing_browse_detail_views.py",
    "backend/listings/listing_browse_detail_views.py",
)

SAVED_SEARCH_SOURCE_PATH_CANDIDATES_V181 = (
    "listings/saved_searches_views.py",
    "backend/listings/saved_searches_views.py",
    "listings/models.py",
    "backend/listings/models.py",
)

SELLER_STORE_SOURCE_PATH_CANDIDATES_V181 = (
    "accounts/views.py",
    "backend/accounts/views.py",
    "accounts/seller_store_views.py",
    "backend/accounts/seller_store_views.py",
    "accounts/tests/test_seller_store_category_tabs.py",
    "backend/accounts/tests/test_seller_store_category_tabs.py",
)

V180_CLOSEOUT_PATH_CANDIDATES_V181 = (
    "listings/listing_views_facade_closeout_audit_v180.py",
    "backend/listings/listing_views_facade_closeout_audit_v180.py",
)


@dataclass(frozen=True)
class ProjectTransitionCategoryTaxonomyReadinessReportV181:
    marker: str
    recommended_next_feature_area: str
    recommended_next_checkpoint: str
    v180_closeout_module_present: bool
    category_model_path: str
    listing_model_path: str
    category_model_exists: bool
    category_model_has_category_class: bool
    category_model_has_name_field: bool
    category_model_has_slug_field: bool
    category_model_has_parent_or_self_relation: bool
    listing_model_has_category_reference: bool
    listing_forms_reference_category: bool
    listing_urls_reference_category: bool
    listing_browse_references_category: bool
    saved_search_sources_reference_category: bool
    seller_store_sources_reference_category: bool
    category_taxonomy_touches_listing_create_update: bool
    category_taxonomy_touches_browse_filters: bool
    category_taxonomy_touches_saved_searches: bool
    category_taxonomy_touches_seller_store_tabs: bool
    implementation_should_start_after_v181: bool
    v182_should_include_model_or_admin_safeguards: bool
    v183_should_include_seed_data: bool
    v184_should_include_navigation_and_filters: bool
    transition_audit_complete: bool


def _first_existing_path_or_none(
    project_root: Path,
    candidates: tuple[str, ...],
) -> Path | None:
    for candidate in candidates:
        path = project_root / candidate
        if path.exists():
            return path
    return None


def _read_first_existing_text(
    project_root: Path,
    candidates: tuple[str, ...],
) -> tuple[Path | None, str]:
    path = _first_existing_path_or_none(project_root, candidates)
    if path is None:
        return None, ""
    return path, path.read_text(encoding="utf-8")


def _read_all_existing_texts(project_root: Path, candidates: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for candidate in candidates:
        path = project_root / candidate
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def build_report(project_root: Path) -> ProjectTransitionCategoryTaxonomyReadinessReportV181:
    category_model_path, category_model_text = _read_first_existing_text(
        project_root,
        CATEGORY_MODEL_PATH_CANDIDATES_V181,
    )
    listing_model_path, listing_model_text = _read_first_existing_text(
        project_root,
        LISTING_MODEL_PATH_CANDIDATES_V181,
    )
    _, listing_forms_text = _read_first_existing_text(
        project_root,
        LISTING_FORMS_PATH_CANDIDATES_V181,
    )
    _, listing_urls_text = _read_first_existing_text(
        project_root,
        LISTING_URLS_PATH_CANDIDATES_V181,
    )
    _, listing_browse_text = _read_first_existing_text(
        project_root,
        LISTING_BROWSE_SOURCE_PATH_CANDIDATES_V181,
    )
    saved_search_text = _read_all_existing_texts(
        project_root,
        SAVED_SEARCH_SOURCE_PATH_CANDIDATES_V181,
    )
    seller_store_text = _read_all_existing_texts(
        project_root,
        SELLER_STORE_SOURCE_PATH_CANDIDATES_V181,
    )

    v180_closeout_module_present = _first_existing_path_or_none(
        project_root,
        V180_CLOSEOUT_PATH_CANDIDATES_V181,
    ) is not None

    category_model_exists = category_model_path is not None
    category_model_has_category_class = "class Category" in category_model_text
    category_model_has_name_field = _has_any(
        category_model_text,
        ("name =", "name=models.", "name = models."),
    )
    category_model_has_slug_field = _has_any(
        category_model_text,
        ("slug =", "slug=models.", "slug = models."),
    )
    category_model_has_parent_or_self_relation = _has_any(
        category_model_text,
        (
            "parent",
            "'self'",
            '"self"',
            "ForeignKey(Category",
            "TreeForeignKey",
            "MPTTModel",
        ),
    )

    listing_model_has_category_reference = _has_any(
        listing_model_text,
        ("category", "Category", "categories.Category"),
    )
    listing_forms_reference_category = _has_any(listing_forms_text, ("category",))
    listing_urls_reference_category = _has_any(
        listing_urls_text,
        ("category", "category_slug", "slug"),
    )
    listing_browse_references_category = _has_any(
        listing_browse_text,
        ("category", "category_slug", "slug"),
    )
    saved_search_sources_reference_category = _has_any(
        saved_search_text,
        ("SavedSearch", "saved search", "category"),
    )
    seller_store_sources_reference_category = _has_any(
        seller_store_text,
        ("category", "category_tabs", "SellerStoreCategoryTabs"),
    )

    category_taxonomy_touches_listing_create_update = bool(
        listing_model_has_category_reference and listing_forms_reference_category
    )
    category_taxonomy_touches_browse_filters = bool(
        listing_browse_references_category or listing_urls_reference_category
    )
    category_taxonomy_touches_saved_searches = bool(saved_search_sources_reference_category)
    category_taxonomy_touches_seller_store_tabs = bool(seller_store_sources_reference_category)

    implementation_should_start_after_v181 = True
    v182_should_include_model_or_admin_safeguards = True
    v183_should_include_seed_data = True
    v184_should_include_navigation_and_filters = True

    transition_audit_complete = all(
        (
            v180_closeout_module_present,
            category_model_exists,
            category_model_has_category_class,
            category_model_has_name_field,
            category_model_has_slug_field,
            listing_model_has_category_reference,
            implementation_should_start_after_v181,
        )
    )

    return ProjectTransitionCategoryTaxonomyReadinessReportV181(
        marker=PROJECT_TRANSITION_CATEGORY_TAXONOMY_READINESS_MARKER_V181,
        recommended_next_feature_area=RECOMMENDED_NEXT_FEATURE_AREA_V181,
        recommended_next_checkpoint=RECOMMENDED_NEXT_CHECKPOINT_V181,
        v180_closeout_module_present=v180_closeout_module_present,
        category_model_path=category_model_path.as_posix() if category_model_path else "",
        listing_model_path=listing_model_path.as_posix() if listing_model_path else "",
        category_model_exists=category_model_exists,
        category_model_has_category_class=category_model_has_category_class,
        category_model_has_name_field=category_model_has_name_field,
        category_model_has_slug_field=category_model_has_slug_field,
        category_model_has_parent_or_self_relation=category_model_has_parent_or_self_relation,
        listing_model_has_category_reference=listing_model_has_category_reference,
        listing_forms_reference_category=listing_forms_reference_category,
        listing_urls_reference_category=listing_urls_reference_category,
        listing_browse_references_category=listing_browse_references_category,
        saved_search_sources_reference_category=saved_search_sources_reference_category,
        seller_store_sources_reference_category=seller_store_sources_reference_category,
        category_taxonomy_touches_listing_create_update=category_taxonomy_touches_listing_create_update,
        category_taxonomy_touches_browse_filters=category_taxonomy_touches_browse_filters,
        category_taxonomy_touches_saved_searches=category_taxonomy_touches_saved_searches,
        category_taxonomy_touches_seller_store_tabs=category_taxonomy_touches_seller_store_tabs,
        implementation_should_start_after_v181=implementation_should_start_after_v181,
        v182_should_include_model_or_admin_safeguards=v182_should_include_model_or_admin_safeguards,
        v183_should_include_seed_data=v183_should_include_seed_data,
        v184_should_include_navigation_and_filters=v184_should_include_navigation_and_filters,
        transition_audit_complete=transition_audit_complete,
    )


def write_markdown_report(
    output_path: Path,
    report: ProjectTransitionCategoryTaxonomyReadinessReportV181,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            [
                "# v181 Project Transition and Category Taxonomy Readiness Audit",
                "",
                report.marker,
                "",
                "## Decision",
                "",
                f"- Recommended next feature area: `{report.recommended_next_feature_area}`",
                f"- Recommended next checkpoint: `{report.recommended_next_checkpoint}`",
                "- Category taxonomy should start after this transition audit, not before it.",
                "",
                "## Baseline",
                "",
                f"- v180 closeout module present: `{report.v180_closeout_module_present}`",
                f"- Category model path: `{report.category_model_path}`",
                f"- Listing model path: `{report.listing_model_path}`",
                f"- Transition audit complete: `{report.transition_audit_complete}`",
                "",
                "## Category model readiness",
                "",
                f"- Category model exists: `{report.category_model_exists}`",
                f"- Category class present: `{report.category_model_has_category_class}`",
                f"- Name field present: `{report.category_model_has_name_field}`",
                f"- Slug field present: `{report.category_model_has_slug_field}`",
                f"- Parent/self relation present: `{report.category_model_has_parent_or_self_relation}`",
                "",
                "## Marketplace integration touchpoints",
                "",
                f"- Listing model has category reference: `{report.listing_model_has_category_reference}`",
                f"- Listing forms reference category: `{report.listing_forms_reference_category}`",
                f"- Listing URLs reference category: `{report.listing_urls_reference_category}`",
                f"- Listing browse source references category: `{report.listing_browse_references_category}`",
                f"- Saved search sources reference category: `{report.saved_search_sources_reference_category}`",
                f"- Seller store sources reference category: `{report.seller_store_sources_reference_category}`",
                "",
                "## Implementation impact",
                "",
                f"- Touches listing create/update: `{report.category_taxonomy_touches_listing_create_update}`",
                f"- Touches browse filters: `{report.category_taxonomy_touches_browse_filters}`",
                f"- Touches saved searches: `{report.category_taxonomy_touches_saved_searches}`",
                f"- Touches seller store tabs: `{report.category_taxonomy_touches_seller_store_tabs}`",
                "",
                "## Recommended sequence",
                "",
                f"- v182 model/admin safeguards: `{report.v182_should_include_model_or_admin_safeguards}`",
                f"- v183 seed data: `{report.v183_should_include_seed_data}`",
                f"- v184 navigation and filters: `{report.v184_should_include_navigation_and_filters}`",
                "",
                "## Guardrails",
                "",
                "- v181 is audit-only.",
                "- v181 does not create, edit, or seed categories.",
                "- v181 does not change production models, forms, views, URLs, templates, or migrations.",
                "- v181 keeps `backend/docs/` out of the repository.",
                "",
            ]
        ),
        encoding="utf-8",
    )
