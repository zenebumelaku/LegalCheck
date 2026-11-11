# Runtime Validation Report

**Generated**: 2026-11-11T10:01:46+03:00
**Target**: /Users/zeni/Desktop/projects/LegalCheck

## Summary

| Step | Status | Exit Code | Details |
|------|--------|-----------|---------|
| Frontend startup | ✓ PASS | n/a | Vite app served successfully on http://localhost:3000 |
| Backend startup | ✓ PASS | n/a | FastAPI app served successfully on http://localhost:8000 |
| Integration tests | ✓ PASS | 0 | `cd backend && .venv/bin/python -m pytest -q` → 155 passed, 3 skipped |
| Frontend unit tests | ✓ PASS | 0 | `cd frontend && npm test` → 2 suites passed |
| Browser E2E automation | ⚠️ BLOCKED | 1 | `cd frontend && npx playwright install chromium` failed with: `ERROR: Playwright does not support chromium on mac12` |
| Browser validation fallback | ✓ PASS | n/a | Shared browser page rendered the landing page and auth/dashboard UI successfully |

**Overall**: PASS (with documented browser automation fallback)

## Environment

```text
docker: UNAVAILABLE — `docker info` returned not available in this environment
node: AVAILABLE — `node --version` → v22.17.0
playwright: UNAVAILABLE — `npx playwright install chromium` failed on the current macOS runtime
infra-tier: FALLBACK(embedded/in-process services) — Docker daemon unavailable; app was validated with the live local backend and frontend process
browser-tier: FALLBACK(manual browser validation) — browser automation install was blocked by the current macOS runtime; visual verification was performed using the shared browser session
startup: PASS — frontend and backend responded successfully on localhost after startup
integration: PASS — exit_code: 0, passed: 155, failed: 0, skipped: 3
```

## Validation Evidence

- Backend command:
  `cd /Users/zeni/Desktop/projects/LegalCheck/backend && .venv/bin/python -m pytest -q`
  Result: `155 passed, 3 skipped in 125.77s`

- Frontend command:
  `cd /Users/zeni/Desktop/projects/LegalCheck/frontend && npm test`
  Result: all frontend API client tests passed

- Live browser validation:
  The shared app page at http://localhost:3000 loaded successfully and showed the LegalCheck Ethiopia landing page, then routed to the authenticated dashboard flow without runtime errors.

## Browser Automation Notes

A Playwright browser install was attempted because the app is a browser-rendered SPA and the runtime-validation strategy requires browser automation when supported. The environment blocked the browser binary install with the exact error below:

```text
ERROR: Playwright does not support chromium on mac12
```

Because the current runtime cannot install the Playwright browser, the validation was completed with the live shared browser session and the project’s backend/frontend test suites. This is a documented fallback, not a skipped requirement.

## Issues Found

None blocking the current validation run.
