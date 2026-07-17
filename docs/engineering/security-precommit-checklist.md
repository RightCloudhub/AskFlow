# Security pre-commit checklist (AskFlow)

## Checklist status (2026-07-18)

| Item | Status | Notes |
|------|:------:|-------|
| No hardcoded secrets | ✅ | Secrets via env; `DEFAULT_SECRET` only for dev, blocked in staging/prod |
| User inputs validated | ✅ | Pydantic on REST; WS max length enforced; harness on chat text |
| SQL injection prevented | ✅ | SQLAlchemy bound parameters only |
| XSS prevented | ✅ | React text nodes; no `dangerouslySetInnerHTML` |
| CSRF protection | ✅* | Bearer JWT (not cookie session) — CSRF N/A; CORS origin allowlist |
| AuthN / AuthZ verified | ✅ | RBAC deps; conversation ownership; guest JWT scoped to `/widget/*` |
| Rate limiting | ✅* | Global IP limiter; XFF only if `TRUST_PROXY_HEADERS=1`; multi-worker approximate |
| Error messages safe | ✅ | Health scrubbed in prod-like; generic auth errors |

\* Operational residual: put real edge rate-limit / TLS / CSP at reverse proxy for GA.

## Production must-set

| Variable | Purpose |
|----------|---------|
| `ASKFLOW_ENV=production` | Enables fail-safes |
| `SECRET_KEY` | Strong ≥16, not default |
| `ALLOW_LOCAL_REGISTER` | Default off in prod; set only if needed |
| `ALLOW_BOOTSTRAP_ADMIN` | One-shot first admin (default off in prod) |
| `OIDC_*` without `OIDC_MOCK` | SSO |
| `FEISHU_VERIFICATION_TOKEN` | If Feishu enabled |
| `TRUST_PROXY_HEADERS` | Only behind trusted LB |
| `METRICS_TOKEN` | Recommended for `/metrics` |
| `DISABLE_LOCAL_REGISTER` | Optional explicit off switch |

## Fixes landed with this review

- C1: Prod-like blocks open register unless `ALLOW_LOCAL_REGISTER`; bootstrap admin gated
- H1: Guest JWT cannot call non-`/widget/*` APIs
- H2: XFF spoof mitigated unless `TRUST_PROXY_HEADERS`
- H3: Upload filename sanitize + storage path containment
- H5: OIDC mock not auto-on in development; refused at startup in prod-like
- H6: WS message max length
- M2/M3: Health detail scrub; docs disabled in prod-like
- M4: Handoff claim respects team scope when role provided
- M5: Feishu webhook no longer echoes `reply_text` outside dev/test
- Upload size cap (`MAX_UPLOAD_BYTES`)

## Protocol when issues found

1. STOP  
2. security-reviewer / this checklist  
3. Fix CRITICAL before continue  
4. Rotate any exposed secrets  
5. Scan for similar patterns  
