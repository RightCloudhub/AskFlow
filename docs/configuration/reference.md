# Complete settings reference

[Configuration guide](README.md)

This reference covers every field in the current application and service-task settings classes, plus the frontend feature override. Use the walkthrough chapters first if you are unsure whether you need a setting.

Unless otherwise stated, set these in the **API** environment or `apps/api/.env` and **restart the API**. Names without an explicit alias use the uppercase field name shown here. Defaults are source defaults, not the possibly different values supplied by your installation.

**Unset** means omit the setting. **Empty text** means an empty string. Use `true`/`false` for booleans, decimal numbers for counts/durations, JSON for designated structured fields, and exact spellings for named choices. Most numeric fields have no strict range validation; keep meaningful positive values unless an explicit off value is documented.

## Runtime and access

See [Basics](basics.md) and [Accounts, access, and hosting](access.md).

| Name | Default | Meaning and limits |
| --- | --- | --- |
| `APP_NAME` | `AskFlow` | API title/root name; does not rebrand the web interface |
| `APP_VERSION` | `0.1.0` | Version label used in process reporting; does not upgrade software or override every package-version display |
| `ASKFLOW_ENV` | `development` | `development`, `test`, `staging`, or `production`; test disables background loops |
| `DEBUG` | `false` | Declared but not currently wired to application debug behavior |
| `API_PREFIX` | `/api/v1` | API route prefix; changing it requires coordinated frontend/proxy changes |
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | JSON array of browser origins; not bare comma-separated text |
| `SECRET_KEY` | `change-me-in-production` | Login-signing secret and fallback webhook secret; replace with a generated private value |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Normal login token lifetime in minutes; widget tokens have a separate fixed lifetime |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm; retain unless changing the authentication integration |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-IP HTTP requests per minute per process; minimum effectively 1; not a distributed or WebSocket-message limit |
| `TRUST_PROXY_HEADERS` | `false` | Trust forwarded client IP for rate limiting; enable only behind a controlled proxy |
| `DISABLE_LOCAL_REGISTER` | `false` | Blocks local self-registration in all modes when true |
| `ALLOW_LOCAL_REGISTER` | `false` | Permits local registration in staging/production, unless explicitly disabled |
| `ALLOW_BOOTSTRAP_ADMIN` | `false` | Allows first-user admin bootstrap in staging/production; development/test permit it separately |
| `METRICS_TOKEN` | Unset | Required `X-Metrics-Token` value for `/metrics` only when set in staging/production |
| `ASKFLOW_PROFILE` | `full` | Feature bundle: `core-only`, `faq-only`, `mvp`, `enterprise`, `full` |
| `ASKFLOW_FEATURES` | Empty text | Comma-separated additions/removals such as `+teams,-mcp`; dependencies may add removed prerequisites back |

## Storage and document processing

See [Storage and indexing](storage.md). File locations depend on the API working directory.

| Name | Default | Meaning and limits |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./askflow.dev.db` | Database address; PostgreSQL uses `postgresql+asyncpg://...`; changing it does not migrate records |
| `REDIS_URL` | Unset | Redis connection for optional indexing queue and shared cancellation; not required for saved service tasks |
| `S3_ENDPOINT` | Unset | Reserved; standard uploads remain local |
| `S3_ACCESS_KEY` | Unset | Reserved S3 credential; not used by the local upload adapter |
| `S3_SECRET_KEY` | Unset | Reserved S3 secret; not used by the local upload adapter |
| `S3_BUCKET` | `askflow` | Reserved bucket name; does not switch storage |
| `CHROMA_PERSIST_DIR` | Unset | Optional local Chroma directory; needs the vector dependency |
| `CHROMA_HOST` | Unset | Optional Chroma host, without scheme/path; takes precedence over local directory |
| `CHROMA_PORT` | `8001` | Chroma server port; bundled container's internal port is 8000 |
| `CHROMA_COLLECTION` | `askflow` | Chroma collection name; keep vectors compatible within a collection |
| `INDEX_ASYNC` | `false` | Queue uploads/reindexing rather than completing them in the request outside test mode |
| `INDEX_WORKER_ENABLED` | `true` | Start in-API index consumer outside test mode |
| `INDEX_WORKER_POLL_SECONDS` | `1.0` | Idle polling delay, seconds; effectively at least 0.2 seconds |
| `INDEX_QUEUE_KEY` | `askflow:index_jobs` | Redis list name; distinguish separate installations sharing Redis |
| `REVISION_STORE_DIR` | `./data/revisions` | Document revision snapshots; changing it does not move old snapshots |
| `MAX_UPLOAD_BYTES` | `15728640` | Maximum upload bytes: 15 MiB; proxy limits may be smaller |
| `CANCEL_TTL_SECONDS` | `300` | Lifetime of cancellation markers in shared cancellation support; not a service-task deadline |

There is no configured upload-directory field in this class: the standard adapter uses `./data/uploads`. There are no global backup scheduling, archive retention, or automatic full-index restore variables.

## Models, search, and conversation context

See [Models and answer quality](models.md) for the required URL form and embedding changes.

| Name | Default | Meaning and limits |
| --- | --- | --- |
| `LLM_BASE_URL` | Unset | Chat service base **without `/v1`**; also fallback embedding base |
| `LLM_API_KEY` | Unset | Chat credential; also fallback embedding credential |
| `LLM_MODEL_GENERATE` | `gpt-4o-mini` | Knowledge-answer model ID |
| `LLM_MODEL_CLASSIFY` | `gpt-4o-mini` | Classification selection/fallback candidate in router; does not replace default rule classifier |
| `LLM_MODEL_REWRITE` | `gpt-4o-mini` | Rewrite selection in router; default query rewriting remains rule-based |
| `LLM_MODEL_SUMMARY` | `gpt-4o-mini` | Summary/draft-assist selection and fallback candidate where used |
| `LLM_TIMEOUT_SECONDS` | `60.0` | Model HTTP timeout, also used for configured embeddings; streamed chat read timeout is separately fixed at 120 seconds |
| `EMBEDDING_BASE_URL` | Unset | Embedding base **without `/v1`**; falls back to chat base |
| `EMBEDDING_API_KEY` | Unset | Embedding credential; falls back to chat credential |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Remote embedding model ID; no remote connection means offline hash embedding |
| `EMBEDDING_DIM` | `384` | Offline vector dimension and configured remote dimension metadata; does not request provider-side resizing |
| `REWRITE_SYNONYM_PATH` | `../../data/samples/query_synonyms.yaml` | Synonym YAML path; use a controlled file of genuine equivalent terms |
| `GROUNDING_THRESHOLD` | `0.35` | Minimum top usable evidence score; lowering accepts weaker evidence |
| `GROUNDING_MIN_HITS` | `1` | Minimum count of usable search hits |
| `GROUNDING_WEAK_SOURCES` | `2` | Number of weak source passages included with an insufficient-evidence response |
| `MAX_QUESTION_CHARS` | `2000` | Maximum question characters in the request guard |
| `MAX_ANSWER_CHARS` | `4000` | Output character bound; current generator also passes this number as model `max_tokens` |
| `MAX_HISTORY_MESSAGES` | `20` | Prior-message context bound; not database retention |
| `MAX_HISTORY_CHARS` | `6000` | Prior-text context bound; not database retention |
| `RETRIEVAL_CACHE_TTL_S` | `60` | Search cache lifetime in seconds; `0` disables it |
| `RETRIEVAL_CACHE_MAX_ENTRIES` | `256` | Per-process cache capacity; minimum effectively 1 |
| `HISTORY_SUMMARY_THRESHOLD` | `12` | Compress history when its length exceeds this count |
| `HISTORY_SUMMARY_KEEP_RECENT` | `4` | Recent messages retained with compressed history; minimum effectively 1 |

These model names document the code defaults. They are not a promise that your provider offers them, or a current price/performance recommendation.

## Request processing, tasks, and staff service

See [Service operations](service.md). The first group of limits applies to the older message/tool loop, not all saved-task execution.

| Name | Default | Meaning and limits |
| --- | --- | --- |
| `MAX_LOOP_STEPS` | `6` | Older tool-loop step budget |
| `MAX_TOOL_CALLS` | `4` | Older tool-loop call budget |
| `MAX_WALL_MS` | `45000` | Older loop wall-time budget in milliseconds: 45 seconds |
| `MAX_RETRIES_PER_TOOL` | `2` | Older loop retry bound; retry behavior also depends on failure type |
| `MAX_SLOT_TURNS` | `3` | Follow-up bound while collecting a missing tool argument such as an order number |
| `INTENT_CLARIFY_THRESHOLD` | `0.45` | Route guard confidence threshold for requesting clarification |
| `HARNESS_POLICY_VERSION` | `1.0.0` | Recorded guard-policy version label; changing it does not install different policy code |
| `SERVICE_TASKS_ENABLED` | `true` | Saved task intake/worker, also requiring the agent feature; test mode suppresses background worker |
| `SERVICE_TASKS_GOALS` | `order_status` | Comma-separated intake allowlist; working additional policies are `ticket_resolution,human_handoff`; empty stops new saved-goal intake |
| `SERVICE_TASK_POLL_SECONDS` | `5.0` | Saved-task worker scan interval; validated minimum 1 second |
| `ORDER_LOOKUP_URL` | Unset | Complete order HTTP endpoint; saved-task path sends order/customer IDs |
| `ORDER_LOOKUP_TOKEN` | Unset | Optional bearer token for the order endpoint |
| `HANDOFF_TIMEOUT_SECONDS` | `300` | Age threshold for unclaimed handoffs to time out |
| `SWEEPER_ENABLED` | `true` | Periodic handoff/SLA checks outside test mode |
| `SWEEPER_INTERVAL_SECONDS` | `60` | Periodic handoff/SLA scan interval; effectively at least 15 seconds |

Saved-task budgets, object-lock duration, order HTTP timeout, SLA policies, and preference retention have separate code or request-level controls. Do not infer environment names for them from the fields above.

## External integrations and optional extensions

See [Accounts](access.md), [Service operations](service.md), and [Channels](channels.md). Configuring a credential does not necessarily enable the corresponding feature or complete its integration.

| Name | Default | Meaning and limits |
| --- | --- | --- |
| `NOTIFY_WEBHOOK_URL` | Unset | Event-receiver URL; unset means local sink rather than external notification |
| `NOTIFY_WEBHOOK_SECRET` | Unset | Webhook signing secret; falls back to `SECRET_KEY` |
| `OIDC_ISSUER` | Unset | Exact identity-provider issuer for ID-token validation |
| `OIDC_CLIENT_ID` | Unset | Expected ID-token audience/client identifier |
| `OIDC_MOCK` | `false` | Development mock identity mode; forbidden in staging/production |
| `MCP_ENABLED` | `false` | Gate for implemented approved-tool registration, not a remote MCP connection |
| `MCP_TOOL_WHITELIST` | `search_knowledge` | Comma-separated allowed names; unknown tools can be echo stubs |
| `SIEM_WEBHOOK_URL` | Unset | Destination for explicit audit push; does not start automatic forwarding |
| `FEISHU_VERIFICATION_TOKEN` | Unset | Feishu event verification value; required for the intended authenticated production setup |
| `FEISHU_APP_ID` | Unset | Feishu outbound-reply application ID |
| `FEISHU_APP_SECRET` | Unset | Feishu outbound-reply application credential |
| `WECOM_TOKEN` | Unset | Supported plain/test verification token; not complete production POST authentication |
| `WECOM_CORP_ID` | Unset | Reserved corporation identifier; no active outbound use |
| `WECOM_AGENT_ID` | Unset | Reserved application identifier; no active outbound use |
| `DINGTALK_APP_SECRET` | Unset | Key for the adapter's supported message-signature format |
| `DINGTALK_APP_KEY` | Unset | Reserved application key; no active outbound use |
| `BOT_PROFILES_JSON` | Empty text | JSON list stored as a string of profile objects; malformed content is ignored by the loader |
| `DEFAULT_BOT_ID` | `default` | Default bot-profile lookup ID; not a separate tenant/security boundary |
| `DEFAULT_LOCALE` | `zh-CN` | Default for limited backend localization; catalog also includes `en-US`; does not translate the web UI |
| `REASONING_ENABLED` | `false` | Enables optional extra steps for matching older-loop intents |
| `REASONING_INTENT_WHITELIST` | `product_faq,troubleshoot` | Exact comma-separated intent names; defaults do not match the normal built-in intent vocabulary |
| `REASONING_MAX_STEPS` | `2` | Additional matching-loop steps; negative values effectively add none |
| `SANDBOX_ENABLED` | `false` | Tool gate only; does not provide sandbox isolation or install an execution service |

## Frontend-only setting

| Name | Default | Location and effect |
| --- | --- | --- |
| `VITE_ASKFLOW_FEATURES` | Unset | `apps/web/.env.local` or web build environment; full comma-separated feature list, without `+`/`-`; restart web dev server or rebuild/redeploy |

Automatic discovery falls back to core-only on failure and currently requires staff/admin access. See [Features](features.md) for matching the frontend list to the backend and supporting customer navigation. Never put credentials in frontend environment values.

## Settings edited in other places

| Configuration | Where to change it |
| --- | --- |
| Intent-to-route overrides | **Admin → 意图路由**; saved in the database |
| Prompt content/active version | **Admin → 提示词模板**; consumption varies by response path |
| Teams and staff membership | **Admin → 技能组** for creation/addition; other changes require integration |
| Account enabled/disabled state | **Admin → 用户管理** |
| Account roles | Operator provisioning or verified SSO role mapping; no role editor in the web page |
| Connector URLs, method, headers, timeout | Authorized connector API; separate database records |
| Knowledge content | **Admin → 知识文档 / 知识草稿** |
| Per-customer saved preferences | Authenticated preference API; no standard preferences page |
| Listening ports, HTTPS, reverse proxy, backups | Server/hosting configuration, outside the application settings classes |
| SLA target durations and full task budgets | Code/integration controls; not browser/env tuning in this version |

For a misspelled, unsupported, or ineffective setting, use [Verification and troubleshooting](troubleshooting.md).
