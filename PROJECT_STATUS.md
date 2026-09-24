# DANA Project Status

## Audit date
2026-09-22

## Current baseline
- Repository: `https://github.com/siavashmehbood/dana.git`
- Branch: `dana-2.0` (PR #1)
- Baseline commit before DANA 2.0 work: `e767706e3af73089e614aa08d745328804810afe`
- Python: 3.14.3
- Django: 5.2.17
- Development database: SQLite
- Production database configuration: PostgreSQL via environment variables

## Completed in this pass
- Repaired and verified the virtual environment/dependencies.
- Added production-aware settings, password validators, secure cookies, HSTS and HTTPS redirect defaults.
- Hardened login and OTP request rate limiting.
- Added checkout idempotency records and payment records.
- Hardened checkout transactions, wallet locking, coupon locking and entitlement uniqueness.
- Added auditable wallet balance-before/balance-after/reference fields.
- Added protected PDF reader endpoint with entitlement checks.
- Added API payload validation and per-user rate limiting.
- Expanded analytics with sales, conversion, ARPU, LTV, AOV, active readers and new users.
- Expanded support ticket states and assignment/priority/category fields.
- Added CI workflow for check, migration validation, tests and deployment security checks.
- Added protected-reader tests, article tests and stronger shop/API tests.
- Added real Zarinpal bank payment request/redirect/callback/verify flow with idempotent finalization and recoverable failure UX.
- Unified text/audio resume behavior across home, dashboard, book detail, library and profile, including legacy audio-only progress compatibility.
- Added event-based reading/listening telemetry and truthful weekly/profile/admin analytics.
- Hardened operational Admin/CMS records for commerce, support, reader activity, authentication devices/sessions and notification delivery audit trails.
- Improved mobile/RTL/accessibility navigation and account recovery UX.
- Added article source provenance, translation version history, validation, rollback/retranslate workflow, original-language fallback and source-rights enforcement.
- Enforced scheduled publication visibility, entitlement expiry, purchase provenance and payment callback state transitions.
- Added chapter integrity constraints, point-ledger idempotency, notification read actions and stronger support validation.
- Added PWA icon and cache version/update behavior.
- Ran `collectstatic` successfully.

## Verification
- `python manage.py check`: PASS
- `python manage.py makemigrations --check`: PASS
- `python manage.py test`: continuously enforced by GitHub Actions on PR #1; latest completed green runs cover the expanded regression suite.
- `python manage.py check --deploy` with production-like environment: PASS
- HTTP smoke tests for home/books/articles/manifest/service-worker: PASS (HTTP 200)
- `collectstatic --noinput`: PASS
- `git diff --check`: PASS

## Remaining production work
- PostgreSQL 17 CI now runs migration checks, applies migrations, and executes the full regression suite on every PR. Production restore rehearsal remains an external deployment operation.
- **EXTERNAL RELEASE REQUIREMENT:** provision real Zarinpal staging/production credentials and run a provider smoke verification. Request/callback/verify, callback-payment authority binding, amount integrity, duplicate-success idempotency, serialized success/cancellation finalization, and retry-safe transient verification failures are covered in-repo. A provider refund adapter remains Post-RC unless automated refunds are required for V1.
- Protected book PDF/audio/chapter-audio use `PRIVATE_MEDIA_ROOT` outside public `MEDIA_ROOT`, expose no storage URL, and are served only through entitlement-aware endpoints with audio Range support. **EXTERNAL RELEASE REQUIREMENT:** production web-server/object-storage configuration must keep `PRIVATE_MEDIA_ROOT` unpublished and migrate legacy private files out of public media.
- **EXTERNAL RELEASE REQUIREMENT:** configure real transactional email/SMS/push credentials and verify delivery in the deployment environment; asynchronous processing remains Post-RC unless deployment volume requires it.
- Add full browser/mobile automated QA and visual regression coverage.
- Add real PWA raster icons if store/install requirements demand them.
- **EXTERNAL RELEASE REQUIREMENT:** configure production monitoring/alerting and a real backup destination, then rehearse restore against production-like infrastructure.

## V1 scope decisions
- Refund is intentionally Post-RC: no customer-facing refund workflow is exposed. Existing `refunded`/wallet audit primitives are retained for a future provider-aware, idempotent reversal workflow; no incomplete automatic refund is promised in V1.
- Password-protected books are safe-disabled for V1 publication: Admin keeps this legacy visibility mode in draft until a complete unlock/session flow exists.
- Publisher/Translator/Tags metadata remains Post-RC; Author/Category/Level cover the current V1 catalog/admin journey and adding schema now is not a release blocker.
- Transactional email/SMS/push delivery providers and background workers remain external/deployment work; in-app notifications are the V1 reliable notification surface.

## Release Candidate gate — 2026-09-24
- Critical repository-fixable remaining: **0 known**.
- High repository-fixable remaining: **0 known**.
- Default CI: **PASS** — DANA CI #1406 on `85420201aca63a330085bf7fab08c49bec806269`.
- PostgreSQL 17 full regression: **PASS** — DANA CI #1406.
- Migration check/apply: **PASS** — both CI jobs.
- Deployment security check: **PASS**.
- Payment: **staging-ready in repository**; success and cancellation callbacks are serialized against the payment row to prevent concurrent final-state races and duplicate provider verification; real-provider smoke remains an EXTERNAL RELEASE REQUIREMENT above.
- Private media: **production-safe in repository**; production serving/storage isolation and legacy migration remain EXTERNAL RELEASE REQUIREMENTs above.
- Critical user/audio/subscription E2E: **covered by the green regression suite**.
- Mobile/RTL and critical accessibility: **V1 usable / critical fixes complete**.
- Admin journey: **operational**; finance, analytics, derived gamification/subscription state, entitlement provenance, and derived user counters are protected from unsafe direct mutation.
- Production configuration: **fail-closed and repository-ready**; deployment secrets/domains/provider credentials/monitoring/backups remain external requirements.

**Repository RC verdict:** PASS. The codebase is Release Candidate ready; production launch remains conditional on completing the explicitly listed EXTERNAL RELEASE REQUIREMENT items.

## Safety note
No force push, destructive reset, repository deletion or production data deletion was performed.


## Post-RC quality gate — 2026-09-24
- Article automatic processing: fixed undefined PDF resolver path, prevented internal translation/status saves from re-queuing processing, and preserved source-field reprocessing.
- Article translation: abstract-only processing avoids unnecessary full-text work; restricted-republish sources translate metadata/abstract without republishing full text; failures remain observable while original content stays available.
- Catalog performance: normal listing/search avoids duplicate full COUNT work before pagination.
- Admin localization: operational field and financial choice labels are Persian across the primary management apps without introducing schema migrations.
- Regression coverage expanded for article processing boundaries, translation fallback/source-rights behavior, and Admin Persian labels.
- Final validation target: DANA CI #1467 on HEAD `c125d293038564791d52b9c5a7f0187ec093ee35`. Repository verdict remains conditional until both default and PostgreSQL jobs pass.
