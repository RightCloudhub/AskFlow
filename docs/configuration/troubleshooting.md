# Verification and troubleshooting

[Configuration guide](README.md) · [Complete reference](reference.md)

Change one group of settings at a time. Retain the previous configuration and verify the actual user action before moving to the next integration.

## Check whether the service started

For the local trial, open `http://localhost:8000/health`. For a hosted service, use the corresponding API health address supplied by the operator.

Read individual entries as well as the top-level status. The current endpoint bases the overall HTTP success on database connectivity; Redis or Chroma can report `down` while the overall status is still `ok`. A Redis entry marked `not_configured` means it was intentionally omitted.

The health check does not validate model keys, every business connector, staff availability, channel reply delivery, or that all uploaded documents were restored to the search index.

## Run a short acceptance check

| Area changed | What to check | What establishes success |
| --- | --- | --- |
| Base configuration | Open health, sign in, create a conversation | Correct database and account are used |
| Features | Inspect **插件与能力**, then use the customer page | Expected backend features load and matching web links work |
| Knowledge/model | Ask a known question and inspect citations/provider requests | Correct document is retrieved and intended model path is confirmed |
| Persistence | Restart in a controlled trial and ask about the same document | Records and required search behavior are restored |
| Staff | Request a person, claim as staff, reply, return to AI | Correct scoped staff access and saved messages |
| Order lookup | Test owned, unowned, and unavailable orders | Verified real status only for an authorized matching order |
| Notifications | Trigger an intended test event | Receiving system confirms the expected event and signature |
| SSO | Sign in with multiple intended roles | Correct account matching and permissions |
| Widget/channel | Send a real message and test follow-up | Reply is visible in the intended channel, not just in server logs |

## Configuration did not take effect

1. Check the exact setting name in the reference. Unknown keys can be ignored.
2. Check that the setting belongs in the API environment rather than the web build or a database record.
3. Confirm the API starts from the folder containing the intended `.env`.
4. Check for an exported shell value or hosting-panel value overriding the file.
5. Restart every affected API process, or rebuild the web app for a frontend setting.
6. Check whether the setting affects new work only, or is documented as reserved/partially integrated.

For a local shell override, `unset SETTING_NAME` removes that named override before the next startup. Replace `SETTING_NAME` with the actual name; do not erase unrelated environment values.

## Common configuration failures

| Symptom | Likely cause and next step |
| --- | --- |
| Startup rejects a weak secret | Generate a real `SECRET_KEY`, apply it to the API process, and restart. Do not disable production mode to bypass the check. |
| Startup rejects `OIDC_MOCK` | Remove mock mode for staging/production and configure verified identity instead. |
| Startup reports a settings/JSON parsing error | Check booleans, numbers, and especially JSON syntax for `CORS_ORIGINS`. Use ordinary quotes, not word-processor quotation marks. |
| Unknown profile/plugin or manifest not found | Use an existing ID and retain the repository's `packages/contracts/features.yaml` when packaging the application. |
| All accounts appear missing | Check the working directory and `DATABASE_URL`; a different SQLite file may have been created. Do not register replacement accounts before locating the retained database. |
| Database connection refused | Verify the actual host, port, credentials, service readiness, and the API's network. Inside containers, `localhost` refers to that container. |
| Migration says table already exists | Have the operator reconcile schema and Alembic history; do not delete a retained database or blindly stamp revisions. |
| Web page opens but requests fail | Check API process, proxying of `/api`, WebSocket upgrade, and unchanged `/api/v1` prefix. `VITE_API_URL` is not implemented. |
| Browser reports CORS rejection | Add the exact page origin as an entry in the JSON list, restart, and verify proxy/address setup. |
| Tickets menu disappears for customers | Current automatic feature discovery requires staff/admin; use a matching non-secret `VITE_ASKFLOW_FEATURES` list and rebuild/restart the web app. |
| A removed plugin remains enabled | A dependent plugin added it back. Inspect dependencies and remove the relevant dependents too. |
| Model requests return 404 | Check that model bases do not include `/v1` or the full endpoint; the clients append their own paths. |
| Model requests return 401/403 or unknown model | Verify provider credentials, entitlement, and exact model IDs privately. |
| Chat model works but uploads fail | Remote embeddings may have been activated by fallback to the chat credentials. Configure a supported embedding service and model. |
| Chroma reports a dimension error | Old and new embeddings may differ. Use a compatible collection and rebuild every relevant document. |
| Health is okay but document search fails after restart | Process-local indexes may be empty. Arrange reindexing/index restoration; the database list is not proof the search index is populated. |
| Chroma configured but health shows memory/failure | Check installation of `.[vector]`, host/port or directory permissions, and operator logs. Memory fallback is not persistent success. |
| Files remain local after S3 configuration | Expected: the standard storage adapter does not use the S3 fields. Preserve local uploads. |
| Documents stay pending | Check `INDEX_ASYNC`, worker availability, test mode, and queue failures. Do not repeatedly upload duplicates. |
| Order task accepted but no result appears | Refresh conversation; check agent feature, task switch, non-test mode, database worker, endpoint, and ID matching. |
| Changing generic `order_status` connector has no effect on tasks | Saved-task order lookup uses `ORDER_LOOKUP_URL`, not that database connector record. |
| Removing a goal did not stop queued work | The allowlist controls new intake. Use appropriate task controls; disabling/restarting the worker does not undo external actions. |
| Nobody sees queued human requests | Verify staff role, enabled team-management feature, membership, and intent scope. |
| SLA/handoff jobs never run | Check `SWEEPER_ENABLED`, mode, and actual running process; interval has a minimum of 15 seconds. |
| Notification is marked `sent_sink` | No external URL was configured; set a real receiver and verify delivery. |
| A messaging callback succeeds but users see no reply | Initial receipt and outbound delivery differ; check that the chosen adapter implements and is configured for the platform's reply mode. |
| A language/bot/MCP setting appears ineffective | Check its documented integration boundary; these settings do not create translated UI, secured bot knowledge partitions, or remote tool connections. |

## Restore the previous configuration

For ordinary limits, routing settings, and feature choices, restore the earlier value in its original location and restart/rebuild as applicable. Test again with a new request.

For storage or embedding changes, restore a consistent combination of configuration and data/index state with the operator. Returning to an old database can omit newer records. Reverting a secret can also alter which issued logins remain valid. External operations already performed cannot be undone by rolling back `.env`.

## Ask for help

Tell the operator which setting names you changed, which page or process is failing, the exact error, the time and timezone, and how you verified it. Include the profile, environment mode, and non-secret host/port details where useful.

Do not attach the whole `.env`, an access-token response, or screenshots of credentials. Redact passwords and tokens from connection strings. For source defects, the operator can use the project's [issue tracker](https://github.com/RightCloudhub/AskFlow/issues).

For operating procedures, see [model/storage maintenance](../../deploy/runbooks/reindex-model-storage.md), [performance and memory](../../deploy/runbooks/performance-and-memory.md), and [monitoring](../observability/monitoring.md).
