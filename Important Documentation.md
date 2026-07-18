# Important Documentation — Defect Audit

**Date:** 2026-07-18
**Scope:** Backend `apps/api` (agent pipeline, RAG/knowledge, auth/security/config, tickets/handoff/cost/SLA, plugin loader/wiring).
**Method:** Static code-logic review only. Per project policy the project was **not run**, no dependencies were installed, and no tests were executed. Each finding was traced through the actual code path; the highest-severity items were additionally re-verified by hand (file/line and grep confirmations noted below).

> This document records **defects found** and the **items that still need to be tested/verified** at runtime. No source code was modified as part of this audit.

---

## Severity legend

| Level | Meaning |
| --- | --- |
| **Critical** | Data loss, auth bypass, or wrong answers to end users in the default configuration. |
| **High** | Incorrect behavior likely in common configs; user- or ops-visible. |
| **Medium** | Wrong behavior in a plausible config or edge case; observability/accuracy impact. |
| **Low** | Latent trap, hardening gap, or dead code with limited blast radius. |

---

## Summary table

| ID | Severity | Area | One-line |
| --- | --- | --- | --- |
| D-01 | High | Ticket SLA | `first_responded_at` is never written → every open ticket false-breaches first-response SLA. |
| D-02 | High | Auth / SSO | OIDC links accounts by email without checking `email_verified` and force-syncs role on every login. |
| D-03 | High* | Middleware | Rate-limit key uses **leftmost** `X-Forwarded-For` (client-spoofable) → per-IP limit bypass behind a proxy. |
| D-04 | Medium | Cost ledger | Budget-seed rows are persisted as `usage` → admin `calls` counts inflated (found independently by 2 reviewers). |
| D-05 | Medium | Plugins | `ASKFLOW_FEATURES=-x` removals are silently re-added by dependency closure (no warning/error). |
| D-06 | Medium | Plugins / safety | Profiles without the `agent` plugin (`faq-only`, `core-only`) lose the `refuse` handler → refusals downgrade to clarify. |
| D-07 | Medium | RAG fusion | Fusion dedup key truncates chunk text to 64 chars → distinct same-doc chunks collapse; evidence/citations dropped. |
| D-08 | Medium | Knowledge parser | Non-UTF-8 (GBK/GB18030) `.txt`/`.md` decodes to mojibake and indexes as noise with no error. |
| D-09 | Medium | Notify / SLA | Webhook/metric side effects fire **before** `db.commit()` → duplicate notifications on rollback. |
| D-10 | Medium | Channels / Feishu | Webhook auth is a static token, not timing-safe, no signature/replay check, fails open when unset. |
| D-11 | Low–Med | Knowledge index | Global in-memory BM25 index is mutated before flush/commit and is lost on restart. |
| D-12 | Low–Med | RAG citations | Citation self-check only matches ASCII `[n]`, not full-width `【1】`/`［1］` → bad citations pass as clean. |
| D-13 | Low–Med | Plugins | `-x` remove-deltas are never validated against known plugins → typos silently no-op. |
| D-14 | Low | Intent | "Clarify weak FAQ" branch is unreachable in rule/offline mode (fallback FAQ conf 0.55, guard is `< 0.5`). |
| D-15 | Low | Slots | Order-slot re-asks `max_slot_turns + 1` times (off-by-one vs the configured limit). |
| D-16 | Low | Middleware | Rate-limit skip uses `path.endswith("/health"|"/metrics")` → any nested route with that suffix bypasses limiting. |
| D-17 | Low | Middleware | Rate-limiter `_hits` dict never evicts idle keys → unbounded memory growth (compounds with D-03). |
| D-18 | Low | Health | `/metrics` is unauthenticated when `METRICS_TOKEN` is unset, even in production. |
| D-19 | Low | RAG fusion | Top-k cut is applied by RRF rank *before* absolute-score re-sort → strongest hit can be starved once real embeddings are wired. |
| D-20 | Low | Code quality | Hardcoded `2000` history-truncation magic number in `harness/policy.py` (violates repo no-magic-number rule). |

\* D-03 is High in a production/behind-load-balancer deployment (`TRUST_PROXY_HEADERS=1`), otherwise inert.

---

## Detailed findings

### D-01 — First-response SLA breaches every open ticket (High) ✅ verified
- **Location:** `apps/api/app/services/ticket/sla/engine.py:59`
- **Root cause:** `evaluate_ticket` computes the first-response breach only while `ticket.first_responded_at is None`, but **no production code ever assigns `first_responded_at`**. Confirmed by grep: the only write is in `tests/unit/test_sla_notify.py:66`; the column exists at `app/models/ticket.py:49`; the status-update path (`app/services/ticket/repository/service.py`) and admin route (`app/api/v1/admin/tickets/routes.py`) update status/assignee/`resolved_at` but never this field.
- **Failure scenario:** An agent replies to a ticket within seconds (status → `processing`). Because `first_responded_at` stays `None`, once `now >= created + fr_min` the scanner returns `BREACHED / first_response` and emits an `SLA_BREACHED` notification for a ticket that was answered on time. The first-response SLA effectively degrades to "resolve within `fr_min` or breach" for **every** unresolved ticket.
- **Suggested fix:** Set `first_responded_at` when a ticket first transitions to `processing` / receives an agent reply (in `update_status` and/or the handoff-reply path).
- **Needs test:** Ticket answered before `fr_min` must not produce a `first_response` breach; a `first_responded_at` write path must exist and be exercised.

### D-02 — OIDC account linking without `email_verified`; unconditional role sync (High) ✅ verified
- **Location:** `apps/api/app/services/auth/oidc.py:144-168` (`login_with_id_token`), `:75-88` (`claims_from_payload`), `:47-60` (`map_roles`).
- **Root cause:** Login links to an existing user purely by `User.email == claims.email` and, for existing users, overwrites `user.role` with the OIDC-mapped role on **every** login. The `email_verified` claim is never read anywhere in the codebase (grep: 0 hits). `map_roles` matches on `r.lower().split("/")[-1]`, so any group path *ending* in `/admin` or `/agent` grants elevated roles.
- **Failure scenario:** If the IdP (or any second federated IdP added later) permits self-asserted/unverified email claims, an attacker presents a validly-signed token with a victim's email and takes over the existing account — including a local admin. Conversely, a real admin who signs in via SSO without the admin group is **silently demoted** to `user`.
- **Note:** JWT signature/issuer/audience validation itself is sound (`jwks.py` pins RS256, verifies iss/aud/exp; `decode_access_token` pins HS256). The risk is the trust model around the email/role claims, not signature forgery. Exploitability depends on the deployed IdP's `email_verified` policy.
- **Suggested fix:** Require `email_verified is True` before linking to an existing local account; link by stable `sub` rather than email; gate the role auto-sync (or make demotion explicit/audited).
- **Needs test:** Token with `email_verified=false` must not link to an existing account; SSO login without admin group must not silently demote an existing admin (or must log/emit the change).

### D-03 — Rate-limit bypass via spoofable X-Forwarded-For (High in prod) ✅ verified
- **Location:** `apps/api/app/middleware/rate_limit.py:39-41`
- **Root cause:** When `trust_proxy_headers` is on, the client key is `x-forwarded-for.split(",")[0]` — the **leftmost** value, which is fully client-controlled. Behind a proxy the trustworthy value is the **rightmost** hop the proxy appended.
- **Failure scenario:** Attacker sends a fresh random `X-Forwarded-For` per request → a new bucket each time → complete per-IP rate-limit bypass, defeating brute-force protection on `/api/v1/auth/login` and `/admin/sso/oidc/login`.
- **Suggested fix:** Take the rightmost XFF entry (or the value the trusted LB sets), or count `trusted_proxy_hops` from the right.
- **Needs test:** With `trust_proxy_headers=1`, N requests each with a distinct spoofed leftmost XFF must still hit the limit.

### D-04 — Budget-seed cost rows persisted and counted as real calls (Medium) ✅ verified
- **Location:** `apps/api/app/services/chat/side_effects/cost.py:19-25` + `app/services/agent/cost/store.py` (`persist_ledger`/`aggregate`) + `app/services/agent/pipeline/runner.py:137-146` (`_seed_cost`).
- **Root cause:** Each turn seeds 4 zero-token entries tagged `meta={"phase":"budget"}`. `CostLedger.summary()` correctly excludes them from token/USD totals (the intent of commit `203566e`), **but** `CostSideEffect.apply` rebuilds a ledger from `turn.cost["entries"]` calling `ledger.record(...)` **without forwarding `phase`** (and `CostLedgerEntry` has no phase column). `persist_ledger` writes every row, and `aggregate()`'s `func.count()` counts them.
- **Failure scenario:** In the default offline mode (no LLM) there are zero real calls, so 100% of persisted cost rows are budget seeds; the admin cost dashboard shows `calls = turns × 4` per purpose at `$0`. Even `transferred`/`blocked` no-op turns persist 4 rows (`_seed_cost` runs before the transferred short-circuit; the cost side effect always runs). Token/USD totals are correct (seeds are zero-token) — so this is accuracy/observability, not billing.
- **Suggested fix:** Skip `phase == "budget"` entries when persisting (or add a `phase` column and exclude in `aggregate`).
- **Needs test:** After an offline turn, persisted cost `calls` for each purpose should be 0, not 4.

### D-05 — Feature-remove deltas silently reversed by dependency closure (Medium) ✅ verified
- **Location:** `apps/api/app/plugins/manifest.py:81-90` (`resolve_features`) + `_expand_deps:93-114`.
- **Root cause:** `selected -= remove` is applied *before* `_expand_deps`, and the dependency closure re-adds any removed plugin still required by a selected one — with no error or warning. The `_expand_deps` docstring claims it will "fail if missing dependency," which the implementation does not do.
- **Failure scenario:** `ASKFLOW_FEATURES=-tools` on `full`/`enterprise`: `mcp` depends on `tools`, so `tools` is re-added and remains fully enabled while the operator believes it is off. Same for `-rag` (re-added by `knowledge`), `-agent` (re-added by `tools`), `-core` (re-added by everything).
- **Suggested fix:** After closure, if a removed id is re-added, raise or log a clear warning naming the depending plugin.
- **Needs test:** `-tools` on `full` should either error or emit a warning; assert `tools` is not silently present without notice.

### D-06 — Profiles without `agent` lose the refuse handler; refusals become clarify (Medium) ✅ verified
- **Location:** `packages/contracts/features.yaml` (`faq-only`, `core-only`) + `app/plugins/builtin/agent.py:28-29` (registers `clarify`/`refuse`) + `app/services/agent/pipeline/runner.py:220-227` (`_dispatch`).
- **Root cause:** The `clarify` and `refuse` route handlers are registered only by the `agent` plugin, but `rag` depends only on `core`, not `agent`. In `faq-only` (`core`+`rag`) the loaded context has no `refuse` handler; `_dispatch` falls back to `handle_clarify` with a `handler_missing:refuse` flag.
- **Failure scenario:** In `faq-only`, an out-of-scope or low-confidence query that the harness routes to `Route.REFUSE` (`_dispatch_known_intent:194-197`) is answered with a clarifying question instead of a refusal — a safety-relevant behavior change. `core-only` registers zero route handlers, so **every** turn becomes a clarify.
- **Suggested fix:** Register `refuse`/`clarify` in the `core` plugin, or make `rag`/those profiles depend on `agent`.
- **Needs test:** Under `ASKFLOW_PROFILE=faq-only`, an out-of-scope query must still refuse (not clarify).

### D-07 — Fusion dedup key truncates chunk text to 64 chars (Medium) ✅ verified
- **Location:** `apps/api/app/services/rag/fusion/rrf.py:34`
- **Root cause:** `key = f"{hit.doc_id}:{hit.text[:64]}"` keys hits by doc_id + only the first 64 chars. Two distinct chunks from the same document that share a 64-char prefix (repeated heading/boilerplate — common in FAQ/policy tables) collapse into one fused hit.
- **Failure scenario:** Distinct evidence is silently merged and the usable-hit count is undercounted; with `grounding_min_hits > 1` this can force a false `weak_evidence` refusal even though ≥2 real chunks matched, and it drops a legitimate citation.
- **Suggested fix:** Key on a stable chunk identity (e.g. `chunk_id`) rather than a text prefix.
- **Needs test:** Two same-doc chunks sharing a long common prefix must remain two distinct fused hits.

### D-08 — Non-UTF-8 text files decode to mojibake and index as noise (Medium)
- **Location:** `apps/api/app/services/knowledge/parser/parser.py:6-14`
- **Root cause:** `.txt`/`.md` are decoded `utf-8` with `errors="replace"` (fallback `latin-1` replace); no charset detection. In this Chinese-first product, a GBK/GB18030 file (the Windows-Chinese default) decodes to U+FFFD noise.
- **Failure scenario:** The document is chunked/indexed as garbage, is never retrievable, and shows `ACTIVE` with no error surfaced.
- **Suggested fix:** Detect encoding (e.g. `charset-normalizer`) before decode, or reject/flag undecodable uploads.
- **Needs test:** Upload a GBK-encoded `.txt`; content must be readable or the upload must fail loudly.

### D-09 — Notifications/metrics emitted before commit → duplicates on rollback (Medium)
- **Location:** `apps/api/app/workers/enterprise_jobs.py:33-49` and `app/services/handoff/timeout.py:75-84`.
- **Root cause:** `notify.emit_safe(...)` (a real external webhook POST + sink append) and metric increments run **before** the single `await db.commit()`. These are non-transactional.
- **Failure scenario:** A later ticket in the sweep raises, or `commit()` fails; the DB rolls back `sla_state`/handoff `TIMED_OUT`/ticket rows, but the webhook was already delivered and the metric incremented. The next cycle re-detects the same rows and re-notifies. The "idempotent per state" guarantee only holds when the commit succeeds.
- **Suggested fix:** Commit first, then emit notifications/metrics for the committed changes (or use a transactional outbox).
- **Needs test:** Force a mid-sweep failure; assert no notification is delivered for the rolled-back change and no duplicate on retry.

### D-10 — Feishu webhook auth: static token, not timing-safe, no signature/replay, fails open (Medium)
- **Location:** `apps/api/app/services/channels/feishu/service.py:57-62,118-129`.
- **Root cause:** Authentication relies only on a static `verification_token` read from the request body, compared with `==` (not constant-time). No `X-Lark-Signature`/timestamp/nonce verification, no replay protection, and `verify_token` returns `True` when no token is configured (fail-open in dev/test).
- **Failure scenario:** The verification token is echoed in every Feishu event body; anyone who observes/leaks one event can forge arbitrary events — injecting messages as any `open_id`, creating conversations, and consuming LLM/cost budget. The `==` comparison additionally leaks the token via timing.
- **Suggested fix:** Verify Lark request signature + timestamp/nonce with replay protection; use `hmac.compare_digest`; fail closed when unconfigured outside dev.
- **Needs test:** Forged event without a valid signature must be rejected; replayed event must be rejected.

### D-11 — In-memory BM25 index mutated outside the transaction and lost on restart (Low–Med)
- **Location:** `apps/api/app/services/knowledge/indexer/service.py:64-93` + `documents.py:66-70`.
- **Root cause:** The process-global BM25 index is cleared/rebuilt via `bm25._docs` before `db.flush()`; the surrounding unit is flushed, not committed. If the request/transaction rolls back afterward (or `flush()` raises after the rebuild), the in-memory index holds chunks the DB does not. The index is memory-only, so all doc mutations are lost on restart (seeds only).
- **Failure scenario:** Retrieval serves chunks for a document the DB considers `FAILED`/absent; after restart, uploaded docs vanish from search.
- **Suggested fix:** Rebuild the index after a successful commit; persist/rehydrate the index on boot.
- **Needs test:** Roll back an index transaction and assert the in-memory index is unchanged; restart and assert previously-indexed docs are still searchable.

### D-12 — Citation self-check ignores full-width brackets (Low–Med)
- **Location:** `apps/api/app/services/rag/citations/verify.py:8` — `CITE_RE = re.compile(r"\[(\d+)\]")`.
- **Root cause:** Only ASCII half-width `[n]` is matched. A Chinese LLM answer citing with `【1】`/`［1］` (very common) yields `citations=[]` and `result="ok"`, so an out-of-bounds/nonexistent citation passes verification as clean.
- **Suggested fix:** Also match full-width bracket forms in `CITE_RE`.
- **Needs test:** An answer citing `【9】` with only 2 sources must be flagged, not pass.

### D-13 — Remove-deltas never validated against known plugins (Low–Med)
- **Location:** `apps/api/app/plugins/manifest.py:86-88`.
- **Root cause:** The `unknown = selected - known` check catches only bad *add* tokens; a `remove` id never enters `selected`, so a typo on the remove side is silently ignored (`+mcpp` errors, `-mcpp` does not).
- **Suggested fix:** Validate remove ids against the known-plugin set too.
- **Needs test:** `ASKFLOW_FEATURES=-mcpp` should raise a `ManifestError`.

### D-14 — "Clarify weak FAQ" branch is unreachable in rule/offline mode (Low)
- **Location:** `apps/api/app/services/agent/intent/classifier.py:82-89`.
- **Root cause:** The guard `rule.intent == Intent.FAQ and rule.confidence < 0.5` cannot fire from rules: the only FAQ-producing rule path is the fallback at `:131-136`, hardcoded to `0.55`, and `0.55 < 0.5` is always False. So a vague non-matching query (e.g. "在吗") routes to RAG, not clarify — the intent added in commit `c8502fd` is dead code in offline mode. *(Confidence: medium — reachable only if an LLM classifier returns a FAQ result with conf < 0.5.)*
- **Suggested fix:** Set the fallback FAQ confidence below the clarify threshold, or compare against `intent_clarify_threshold`.
- **Needs test:** A vague FAQ-fallback query should route to clarify, not RAG.

### D-15 — Order-slot re-asks one turn more than `max_slot_turns` (Low)
- **Location:** `apps/api/app/services/agent/slots/state.py:125-131`.
- **Root cause:** `start_order_slot` seeds `turns_waited=0`, and `decide` abandons when `state.turns_waited + 1 > self.max_turns`. With `max_slot_turns=3`, the user is re-asked on stored counts 1/2/3 and abandoned only on the 4th reply.
- **Suggested fix:** Align the comparison with the configured limit (or document the intended +1).
- **Needs test:** With `max_slot_turns=3`, exactly 3 asks then abandon.

### D-16 — Over-broad rate-limit skip suffix match (Low)
- **Location:** `apps/api/app/middleware/rate_limit.py:60` — `path.endswith("/health")` / `path.endswith("/metrics")`.
- **Root cause:** Any current/future route whose path ends with those suffixes bypasses rate limiting entirely.
- **Suggested fix:** Match exact/known paths, not suffixes.

### D-17 — Unbounded rate-limiter memory (Low)
- **Location:** `apps/api/app/middleware/rate_limit.py:33,66-68`.
- **Root cause:** `self._hits` (`defaultdict(deque)`) is never pruned of idle client keys; only per-key old timestamps are trimmed. With spoofable XFF (D-03) or many distinct IPs the dict grows without bound.
- **Suggested fix:** Evict keys with empty buckets; cap dict size or move to Redis.

### D-18 — `/metrics` unauthenticated when token unset, even in prod (Low)
- **Location:** `apps/api/app/api/v1/health/routes.py:71-80` — `_metrics_authorized` returns `True` whenever `METRICS_TOKEN` is unset, and `/metrics` is on the rate-limit skip list.
- **Root cause:** Fail-open in production if ops forgets to set the token → intent/route/cost/error counters are publicly scrapeable.
- **Suggested fix:** In production, require `METRICS_TOKEN`; fail closed if unset.

### D-19 — Top-k cut before absolute-score re-sort can starve the strongest hit (Low)
- **Location:** `apps/api/app/services/rag/fusion/rrf.py:52-59`.
- **Root cause:** `fuse_hits` selects top-`k` **by RRF rank first**, then re-sorts survivors by absolute score. A hit with the highest absolute grounding score but low RRF rank (present in only one channel) can be dropped before it reaches the grounding evaluator. Currently masked because `VectorStore` reuses BM25 (`vector/store.py:26`) so both channels agree; becomes a real bug once real embeddings are wired.
- **Suggested fix:** Retain top-k by both RRF and absolute score, or widen the slice before the grounding cut.

### D-20 — Hardcoded history-truncation magic number (Low, code quality)
- **Location:** `apps/api/app/services/agent/harness/policy.py:190` — content truncated at literal `2000`.
- **Root cause:** Repo policy forbids magic numbers (`CLAUDE.md`, `rules/code-quality.md`); this bound should be a named `Settings` field (e.g. `max_history_msg_chars`). Note it also decouples from `max_question_chars`, so the `MSG_TOO_LONG` "2000 字" copy and this constant can silently diverge.
- **Suggested fix:** Extract to a `Settings` constant.

---

## Verified NOT defective (checked, no action needed)

These were examined and found correct — recorded to save reviewer time:

- **Traversal safety:** `LocalObjectStorage._resolved_path` rejects `..` and absolute-segment injection via `resolve()` + `relative_to(root)`.
- **Chunker:** `chunk_text` has no off-by-one and cannot infinite-loop (`overlap` capped at `size-1`, stride ≥ 1). No division-by-zero in RAG (`query_coverage` guards empty query; RRF `k` constant).
- **Concurrency:** Handoff `enqueue` dedupe + `claim` CAS, ticket `create_or_get_open`, and the handoff timeout sweeper all use partial unique indexes + `begin_nested`/`IntegrityError` retry or row-count CAS — race-safe.
- **JWT:** No HS/RS algorithm-confusion path; `decode_access_token` pins HS256, JWKS validator pins RS256 and verifies iss/aud/exp.
- **Auth surface:** Bearer-token APIs (no cookies) → CSRF N/A; conversation access is ownership-checked (no direct IDOR on conversation IDs); `assert_startup_safe` blocks weak `SECRET_KEY`/`OIDC_MOCK` outside dev/test.
- **Plugin graph:** Dependency closure and topological sort handle diamonds and detect true cycles; no route-handler key collisions across builtins; middleware order matches its documented comment (CORS outermost).
- **Pipeline:** Loop budget/retry accounting consistent; slot `pending_slot` reliably cleared on filled/abandon; `OUT_OF_SCOPE → REFUSE` override holds; security copy/thresholds are code constants (harness invariant intact).

---

## Runtime verification checklist (to test when the stack is run)

Because the project was not executed, the following must be confirmed at runtime. Ordered by priority.

1. **[D-01]** Ticket answered before `fr_min` → assert **no** `first_response` breach; confirm a code path writes `first_responded_at`.
2. **[D-02]** OIDC token with `email_verified=false` → must not link to an existing account; SSO login without admin group → existing admin not silently demoted.
3. **[D-03]** `trust_proxy_headers=1`, N requests with distinct spoofed leftmost `X-Forwarded-For` → still rate-limited.
4. **[D-04]** One offline turn → persisted cost `calls` per purpose == 0 (not 4); `transferred`/`blocked` turns persist no cost rows.
5. **[D-05]** `ASKFLOW_FEATURES=-tools` on `full` → operator gets an error/warning; `tools` not silently active.
6. **[D-06]** `ASKFLOW_PROFILE=faq-only`, out-of-scope query → refuses (not clarifies).
7. **[D-07]** Two same-doc chunks with a shared 64+ char prefix → remain two fused hits.
8. **[D-08]** GBK-encoded `.txt` upload → readable content or a loud failure (no silent mojibake ACTIVE doc).
9. **[D-09]** Forced mid-sweep failure → no notification for the rolled-back change; no duplicate on retry.
10. **[D-10]** Feishu event with invalid/absent signature or replayed timestamp → rejected.
11. **[D-11]** Rolled-back index txn → in-memory BM25 unchanged; restart → prior docs still searchable.
12. **[D-12]** Answer citing `【9】` with 2 sources → flagged, not `ok`.
13. **[D-13]** `ASKFLOW_FEATURES=-mcpp` (typo) → `ManifestError`.
14. **[D-14]** Vague FAQ-fallback query → clarify, not RAG.
15. **[D-15]** `max_slot_turns=3` → exactly 3 asks then abandon.
16. **[D-16..D-20]** Nested `/x/metrics` route not skipped; rate-limiter memory bounded; `/metrics` requires token in prod; strongest-score hit reaches grounding with real embeddings; history-bound constant extracted to `Settings`.

---

# Important Documentation — Frontend: Admin JSON Display & Global Style Override

**Date:** 2026-07-18
**Scope:** Frontend `apps/web` — a new dependency-free JSON tree viewer plus a global style-override layer for the admin console.
**Method:** Static code-logic review only. Per project policy the project was **not run**, no dependencies were installed, and no `tsc`/`vite`/metrics command was executed. Compliance and behavior were reasoned through by hand; the items below must be confirmed once the stack is built/run.

## What changed & why

Admin pages dumped machine data as raw, **unstyled** `<pre>{JSON.stringify(...)}</pre>` blocks — several not even pretty-printed (`AuditPage`, `LaunchCardsPage` rendered single-line JSON). There was no `pre` styling in the stylesheet at all, so these overflowed horizontally and were hard to scan. Two coordinated changes:

1. **`JsonView` component** (`apps/web/src/components/common/json/*`) — a collapsible, syntax-coloured JSON tree with a toolbar (expand / collapse / raw / copy), collapsed-node summary chips (`{ 5 字段 }` / `[ 3 项 ]`), and a compact inline variant for list rows. **Zero new dependencies** (built from React + CSS only — required by the "code only / no dependency download" constraint and consistent with the project's offline-first ethos).
2. **Global style override** — upgraded `:root` design tokens in `global.css` (neutral ramp, semantic colours, JSON-syntax colours, a real monospace stack, elevation/motion tokens) + a `theme.css` polish layer (focus rings, button/row micro-interactions, clearer admin-nav active state, base `pre`/`code-block` treatment, quieter scrollbars).

### Design decisions (rationale)
- **No CDN web fonts.** This is a self-hostable, offline-first enterprise product; a Google-Fonts `<link>` would break air-gapped installs and leak requests. Distinctiveness comes from the monospace data treatment, colour, spacing, and wayfinding — not a downloaded typeface. The sans stack keeps the original zh-CN fallbacks (`PingFang SC`/`Noto Sans SC`).
- **Token-based override.** Visual change is driven mostly by `:root` tokens (cascades to existing class rules) + an additive `theme.css`, so existing page markup keeps working unchanged (low regression risk).
- **File-size discipline.** New styling went into separate files (`theme.css` 168 lines, `json-view.css` ~190 lines) instead of growing `global.css`. `global.css` is 500 lines (was already 459) but CSS is **not** scanned by `scripts/ops/check_code_metrics.py` (it only lints `.py`/`.ts`/`.tsx`). All new/modified `.ts`/`.tsx` are well under the 300-line gate (largest is `JsonNode.tsx`, 120).

## Files

**Added**
- `apps/web/src/components/common/json/jsonUtils.ts` — pure helpers (type classify, format leaf, entries, summary label, pretty-print, clipboard).
- `apps/web/src/components/common/json/JsonNode.tsx` — recursive node renderer (container/primitive, per-node collapse).
- `apps/web/src/components/common/json/JsonView.tsx` — public component (toolbar + tree/raw + copy).
- `apps/web/src/components/common/json/index.ts` — barrel export.
- `apps/web/src/styles/json-view.css` — viewer styles.
- `apps/web/src/styles/theme.css` — global polish/override layer.

**Modified**
- `apps/web/src/styles/global.css` — expanded `:root` token set + `--font-sans`/`--font-mono`.
- `apps/web/src/main.tsx` — import `theme.css` and `json-view.css`.
- Admin pages now render `JsonView` instead of raw `<pre>`: `CostsPage`, `AgentRunsPage` (step detail + cost), `ConnectorsPage` (state type changed `string → object|null`), `AuditPage`, `SlaPage` (counts + scan), `QcPage`, `LaunchCardsPage`. `PromptsPage` keeps a `<pre className="code-block">` for prompt *text* (not JSON), now styled by `theme.css`.

## Component behaviour (for reviewers)
- `expandDepth` semantics: a node is open iff `depth < expandDepth` (root = depth 0). `initialExpandDepth` default **2** (root + first level open). `0` → root collapsed to a summary chip; `1` → root open, children collapsed.
- Expand-all / collapse-all **remount** the tree (React `key` bump) so every node re-derives its open state; this intentionally resets manual per-node toggles.
- `compact` renders the tree only (no toolbar/card chrome) for use inside list rows.
- Per-page config used: Costs `full` (guarded on load) · AgentRuns step `compact depth1` · AgentRuns cost `full` · Connectors `full` · Audit `compact depth0` (one chip per log row) · SLA counts/changes `full` · QC `full` (guarded) · LaunchCards `compact depth2`.

## Static verification performed
- Grep confirms **no** `<pre>{JSON.stringify...}` remains in `apps/web/src/pages/admin` (only the intentional `PromptsPage` `.code-block`).
- Every page using `<JsonView>` imports it (7/7).
- All new/modified `.ts`/`.tsx` ≤ 300 lines (enforced TS metric). By-hand check of function length ≤ 50 / nesting ≤ 3 / no magic numbers (extracted `DEFAULT_EXPAND_DEPTH`, `EXPAND_ALL_DEPTH`, `COLLAPSE_DEPTH`, `ROOT_DEPTH`, `COPY_FEEDBACK_MS`).
- CSS class names cross-checked against the JSX (`.jv*`).

## Runtime verification checklist (must confirm when built/run)
1. **Type/build:** `cd apps/web && npm run build` (`tsc --noEmit` + `vite build`) passes — confirms the `unknown` prop, inline `type` imports, and `strict`/`noUnusedLocals` compliance.
2. **Metrics gate:** `python3 scripts/ops/check_code_metrics.py` → 0 violations (not run here per policy).
3. **Each admin page renders** its JSON as a tree: `/admin/costs`, `/admin/agent-runs` (query a run), `/admin/connectors` (试调用), `/admin/audit`, `/admin/sla`, `/admin/qc`, `/admin/launch-cards`.
4. **Interactions:** carets expand/collapse a node; toolbar 展开/折叠 reflow the whole tree; 原文/树视图 toggles raw pretty-printed JSON; 复制 copies and shows 已复制.
5. **Clipboard limitation:** `navigator.clipboard` needs a **secure context** (https or `localhost`). On plain-HTTP LAN access, copy silently no-ops (no 已复制) — verify the button degrades gracefully; consider an exec-command fallback if HTTP hosting is required.
6. **Compact rows** (Audit, AgentRuns steps, LaunchCards) stay tidy: collapsed chip per audit row expands on click; no card chrome; monospace at 0.82rem.
7. **Edge data:** empty object/array renders `{}`/`[]`; `null`/nested arrays/long string values wrap instead of overflowing; a `null` root (pre-load) is guarded by a "加载中…" line on Costs/QC.
8. **Accessibility:** toggle buttons are keyboard-focusable with a visible focus ring (`--ring`) and expose `aria-expanded`/`aria-label`; verify tab order and screen-reader announcement.
9. **Contrast:** JSON syntax colours on white/`--panel-2` meet AA (key `#3538cd`, string `#0e7490`, number/warn `#b45309`, boolean `#7c3aed`, null `#64748b`) — spot-check in the running UI.
10. **No visual regression** on user-facing pages (Login/Chat/Tickets/Widget) from the token/`theme.css` changes (buttons, inputs, focus, scrollbars).

## Known limitations
- No list virtualization — extremely large payloads render every node (acceptable for current admin payloads; revisit if run/cost detail grows huge).
- Expand-all/collapse-all resets manual per-node state (by design, via remount).
- Raw/copy toolbar is available only in non-`compact` mode.
