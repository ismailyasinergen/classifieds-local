# v149 Project-wide Refactor Candidate Audit

PROJECT_REFACTOR_CANDIDATE_AUDIT_V149

## Purpose

After v148, `backend/listings/views.py` has no remaining low-risk helper extraction candidates.
This audit creates a project-wide map of the next safest refactor lanes without changing application behavior.

## Non-goals

- Do not move code.
- Do not rename modules.
- Do not change imports.
- Do not change URLs, templates, models, migrations, or behavior.

## Summary

- Root: `C:\Users\ismai\Desktop\classifieds_local`
- Scanned Python files: 115
- Parse errors: 0
- Large files, 600+ lines: 4
- High-complexity files: 2
- Medium-complexity files: 6

## Recommended next candidate

- Path: `backend\listings\views.py`
- Lines: 2328
- Top-level functions: 48
- Top-level classes: 9
- Methods: 18
- Imports: 34
- View-like functions: 45
- Risk label: high_complexity
- Likely lane: view_module_split_or_helper_extraction

## Top candidates

| Rank | Path | Lines | Functions | Classes | Methods | Imports | View-like funcs | Risk | Likely lane |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `backend\listings\views.py` | 2328 | 48 | 9 | 18 | 34 | 45 | high_complexity | view_module_split_or_helper_extraction |
| 2 | `backend\accounts\appeal_views.py` | 2130 | 42 | 0 | 0 | 18 | 38 | high_complexity | general_module_review |
| 3 | `backend\accounts\store_views.py` | 843 | 9 | 0 | 0 | 11 | 7 | medium_complexity | general_module_review |
| 4 | `backend\accounts\seller_report_action_views.py` | 565 | 19 | 0 | 0 | 10 | 18 | medium_complexity | general_module_review |
| 5 | `backend\accounts\trust_safety_views.py` | 616 | 15 | 0 | 0 | 11 | 0 | medium_complexity | general_module_review |
| 6 | `backend\scripts\sahibinden_category_tree_fetcher.py` | 460 | 18 | 1 | 4 | 14 | 0 | medium_complexity | general_module_review |
| 7 | `backend\scripts\sahibinden_schema_tool.py` | 431 | 18 | 0 | 0 | 11 | 0 | medium_complexity | general_module_review |
| 8 | `backend\accounts\models.py` | 473 | 0 | 7 | 19 | 5 | 0 | low_complexity | model_manager_or_domain_service_audit |
| 9 | `backend\listings\attribute_filters.py` | 414 | 16 | 0 | 0 | 3 | 0 | low_complexity | general_module_review |
| 10 | `backend\listings\saved_search_notifications.py` | 312 | 16 | 2 | 1 | 10 | 3 | low_complexity | general_module_review |
| 11 | `backend\listings\saved_searches.py` | 383 | 13 | 0 | 0 | 3 | 1 | low_complexity | general_module_review |
| 12 | `backend\listings\attribute_schema.py` | 272 | 18 | 0 | 0 | 4 | 0 | medium_complexity | general_module_review |
| 13 | `backend\listings\models.py` | 372 | 0 | 5 | 20 | 6 | 0 | low_complexity | model_manager_or_domain_service_audit |
| 14 | `backend\listings\admin.py` | 219 | 7 | 6 | 5 | 5 | 4 | low_complexity | admin_config_split |
| 15 | `backend\accounts\trust_safety_dashboard_views.py` | 317 | 10 | 0 | 0 | 8 | 6 | low_complexity | general_module_review |

## Safe sequencing rule

Choose only one lane for the next checkpoint. Prefer audit-only or test-only checkpoints before moving behavior-bearing code.
