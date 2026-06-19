# Roadmap Status

Current checkpoint: `project-checkpoint-v1`

## Completed

- Appeals queue date filters
- Action Log date filters and CSV export
- Appeal evidence filters
- TrustSafetyEvent model
- accounts/views.py refactor into focused modules
- Suspension and appeal automated tests
- Header/admin navigation cleanup
- Notices pagination
- Seller reports pagination
- Private media download protection
- Production-ready settings
- Appeal extra-evidence deadline flow
- Appeal extra-evidence upload layout
- Appeal extra-evidence multi-batch upload
- Evidence gallery and seller no-delete rule
- Evidence stage labels: initial vs extra
- Admin evidence gallery
- Admin evidence stage correction tool
- Audit event for admin evidence label correction
- Appeal URL regression tests
- Core page smoke tests
- Stable local demo users
- Email-or-username login
- Local demo login autofill dropdown

## Current verification

Run: ./scripts/checkpoint.sh

Expected: Django check passes, full test suite passes, Docker containers start, classifieds_web is up.
