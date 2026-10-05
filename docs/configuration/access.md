# Accounts, access, and hosting

[Configuration guide](README.md) · Next: [Service operations](service.md)

The website administrator manages people and content. The hosting operator manages the server, network address, credentials, and environment. Work with that operator when making an installation available to others.

## Choose the environment mode

| `ASKFLOW_ENV` | Intended use | Important behavior |
| --- | --- | --- |
| `development` | Local development/trials | Local registration allowed unless disabled; first account may become admin; interactive API docs available |
| `test` | Automated testing | Background loops disabled; do not use as a customer-service mode |
| `staging` | A deployment rehearsal | Production-like registration restrictions, secret checks, and hidden interactive API docs |
| `production` | A shared operational service | Same startup safeguards as staging; real integrations still need verification |

The default is `development`. Setting `production` does not install HTTPS, create backups, configure external providers, or make a prototype integration complete.

## Set the login-signing secret

Use a locally generated unpredictable value for `SECRET_KEY`; see [First setup](first-setup.md). Staging and production reject known weak defaults and values shorter than 16 characters. Passing that minimum check is not a reason to use a memorable password instead of a generated secret.

All instances serving the same installation should use the intended shared signing key. Changing it invalidates existing signed logins; expect users to sign in again. It also changes notification signing if no separate `NOTIFY_WEBHOOK_SECRET` was supplied.

`ACCESS_TOKEN_EXPIRE_MINUTES` defaults to `1440` (24 hours) for normal tokens. `JWT_ALGORITHM` defaults to `HS256`; retain it unless the operator is changing the authentication design. Widget guest tokens use a separate fixed two-hour lifetime, not this normal-token setting.

## Decide how accounts are created

| Setting | Default | Effect |
| --- | --- | --- |
| `DISABLE_LOCAL_REGISTER` | `false` | When true, blocks local self-registration in all modes |
| `ALLOW_LOCAL_REGISTER` | `false` | Explicitly permits local registration in staging/production unless disabled above |
| `ALLOW_BOOTSTRAP_ADMIN` | `false` | In staging/production, allows the first registered account in an empty user database to become admin |

In development/test, first-user administrator bootstrap is allowed independently of `ALLOW_BOOTSTRAP_ADMIN`. In staging/production, the allow-registration and allow-bootstrap flags are separate: enabling bootstrap does not also open registration.

To establish the first administrator of a **new** production-mode installation through local registration, the operator can restrict network access during setup, temporarily enable both allow flags, register the intended account, verify its admin role, then remove bootstrap permission and decide whether ongoing self-registration should remain open. Restart after each environment change.

An existing first user is not promoted by setting the bootstrap flag. The standard user-management page cannot edit roles or reset passwords. Arrange existing-account role changes through the operator or company sign-in integration; do not reset a retained database to regain access.

For an installation where accounts are provisioned separately:

```dotenv
DISABLE_LOCAL_REGISTER=true
ALLOW_LOCAL_REGISTER=false
ALLOW_BOOTSTRAP_ADMIN=false
```

These settings block registration, not existing username/password login. Confirm an appropriate sign-in/provisioning route is working before closing self-registration.

## Configure company sign-in

Company sign-in uses an **identity provider**, the service that authenticates your organization's users. Ask its administrator for the exact issuer and client/audience identifier and agree which roles it will send.

```dotenv
OIDC_ISSUER=https://identity.example.com/realms/company
OIDC_CLIENT_ID=askflow
OIDC_MOCK=false
```

Enable the `sso` feature, restart, and have the identity operator integrate the verified-ID-token exchange at `POST /api/v1/admin/sso/oidc/login`. This expects an ID token already obtained from the provider. The standard login page has no SSO button, redirect flow, or callback setup wizard. Environment values alone do not complete browser sign-in.

Default role mappings are `admin`/`administrator` → administrator, `agent`/`support` → staff, and `user` → customer. The highest recognized role wins; unrecognized roles become customer. Roles/groups supplied by the provider can update an existing account's role at sign-in. Account matching currently uses email, so have the identity administrator validate claims and matching before rollout.

`OIDC_MOCK=true` accepts mock test identities in development and is forbidden at startup in staging/production. Keep it false for real identity validation.

Verify sign-in as a customer and as staff/admin, including a disabled account and an account that should lack administrator rights. Keep an agreed account-recovery route.

## Connect the browser to the backend

The standard frontend calls relative `/api/v1/...` paths on the same website. There is no implemented `VITE_API_URL` setting. In development, Vite proxies `/api` and WebSocket traffic to `127.0.0.1:8000`.

For hosting, have the operator serve the built web files and route `/api` to the API, including WebSocket upgrade support and suitable streaming timeouts. Client-side page routes such as `/tickets` need to return the web application. A successful home page alone does not prove chat proxying works.

Keep `API_PREFIX=/api/v1` unless the frontend and proxy are deliberately changed together. Changing this setting alone breaks the standard web requests. Backend listening address/port are server-launch arguments such as Uvicorn's `--host` and `--port`, not `API_PORT` variables. The web development port is set in Vite configuration, normally 5173.

## Set allowed browser origins

An **origin** is the scheme, host, and port where a browser page runs, for example `https://support.example.com`. CORS is the browser's cross-origin access check; it is not an authentication system or a firewall.

```dotenv
CORS_ORIGINS='["https://support.example.com"]'
```

Use the actual page origins, without URL paths. Restart the API. JSON list syntax is required by the settings loader. The default contains `http://localhost:5173` and `http://127.0.0.1:5173`.

Allowing a second origin does not redirect the frontend's relative API requests to another server. The operator still needs a suitable proxy or frontend change. For a hosted widget, browser embedding policy and frame headers are additional hosting decisions.

## Set request limits and monitoring access

`RATE_LIMIT_PER_MINUTE=60` is the default per-IP HTTP request limit. Shared networks may put many users behind one IP. Set a measured limit and test; this is not a per-customer billing or model-spend cap.

`TRUST_PROXY_HEADERS=false` is the default. Set it true only when the API is reachable through a trusted proxy that controls forwarded client-address headers. Otherwise callers could supply misleading addresses. Restart and have the operator verify the address used for rate limiting.

`METRICS_TOKEN` optionally protects `/metrics` using the `X-Metrics-Token` header in staging/production. It is not enforced in development/test. Configure the monitoring collector accordingly and keep monitoring endpoints on the intended network. It does not protect `/health` or ordinary API routes.

## Example production-mode decisions

This is a template to adapt after accounts, storage, and hosting are arranged, not a deploy-and-forget recipe:

```dotenv
ASKFLOW_ENV=production
SECRET_KEY=REPLACE_WITH_A_GENERATED_SECRET
DATABASE_URL=postgresql+asyncpg://askflow:REPLACE_WITH_DATABASE_PASSWORD@db.example.com:5432/askflow
ASKFLOW_PROFILE=full
DISABLE_LOCAL_REGISTER=true
ALLOW_BOOTSTRAP_ADMIN=false
OIDC_MOCK=false
CORS_ORIGINS='["https://support.example.com"]'
TRUST_PROXY_HEADERS=false
METRICS_TOKEN=REPLACE_WITH_A_SEPARATE_MONITORING_SECRET
```

Add only the model, storage, task, and channel connections you intend to use. Apply the environment to all relevant processes, align the web feature list, and complete [verification](troubleshooting.md). The [deployment checklist](../../deploy/checklists/pilot-integration.md) contains the operator's further acceptance work.
