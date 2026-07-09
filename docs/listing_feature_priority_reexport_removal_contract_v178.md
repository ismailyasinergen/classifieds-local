# v178 Listing Feature Priority Facade Re-export Removal Contract

LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_V178

## Summary

- Target facade re-export: `listing_feature_priority_update`
- Target source module: `listing_promotion_views`
- Migrated dependency file: `listings/urls.py`
- Dedicated import now used by migrated dependency: `from listings.listing_promotion_views import listing_feature_priority_update`
- Views path: `listings/views.py`
- Views total lines: `155`
- Target still re-exported by facade: `True`
- Target source module defines name: `True`
- Target dependency cleared by v177: `True`
- Target is only v175 candidate: `True`
- Target is only v176 missing migration name: `True`
- v177 target group migrated: `True`
- v177 safe to remove facade re-export: `False`
- Target migration record count after v177: `0`
- Contract ready for later removal: `True`
- Safe to remove in v178: `False`
- Recommended next checkpoint: `v179 may remove only listing_feature_priority_update from the listings.views facade re-export after this contract remains green.`

## Guardrails

- v178 is a contract-only checkpoint.
- Do not edit `backend/listings/views.py` in v178.
- Do not remove `listing_feature_priority_update` from the facade in v178.
- Do not change `backend/listings/urls.py` in v178.
- A later checkpoint may remove only the contracted facade re-export if all guards stay green.
