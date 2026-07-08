# v151 Listing Promotions Contract Tests

LISTING_PROMOTIONS_CONTRACT_V151

## Purpose

Before moving the `listing_promotions` lane out of `backend/listings/views.py`, v151 locks the current POST-only behavior with focused contract tests.

## Current v150 split-lane facts

- Target file: `backend/listings/views.py`
- Lane: `listing_promotions`
- Definition: `listing_feature_priority_update`
- Definition lines: 433-452
- Line count: 20
- URL route: `listings/<int:pk>/feature-priority/`
- URL name: `listing_feature_priority_update`
- Route params: `pk`
- Split readiness: `candidate_for_first_split`

## Contract locked by v151

- The v150 audit still identifies exactly one `listing_promotions` definition.
- The promotion URL name and callback remain stable.
- Anonymous requests redirect to login.
- Anonymous GET requests redirect to login before method handling.
- Authenticated GET requests return 405 Method Not Allowed because the promotion endpoint is POST-only.
- The listing owner can POST to the promotion flow without 403/404/405.
- A non-owner POST cannot render the owner promotion flow as a successful 200 response.

## Non-goals

- Do not move the promotion view yet.
- Do not change URL routing yet.
- Do not change templates, permissions, redirects, messages, promotions logic, models, migrations, or behavior.

## Next safe step

If v151 passes and is committed, v152 can move `listing_feature_priority_update` into a dedicated listing promotion view module while keeping the public import and URL behavior unchanged.
