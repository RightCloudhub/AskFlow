# Service operations

[Configuration guide](README.md) · Next: [Channels and extensions](channels.md)

These settings control work beyond a knowledge answer: order lookups, saved tasks, staff queues, service-time checks, and notifications.

## Configure saved service tasks

A service task is a saved request that can continue in a background worker. Its records are stored in the database; Redis is not required for this scheduler.

```dotenv
SERVICE_TASKS_ENABLED=true
SERVICE_TASKS_GOALS=order_status
SERVICE_TASK_POLL_SECONDS=5
```

The `agent` feature must also be enabled. The API starts the worker automatically outside test mode. The poll interval is in seconds and must be at least `1`; it is a scan interval, not a guaranteed customer response time.

| Goal | Current meaning |
| --- | --- |
| `order_status` | Check the authenticated customer's order; enabled by default |
| `ticket_resolution` | Register a ticket; opt-in, and completion only verifies registration |
| `human_handoff` | Arrange handoff; opt-in, with separate staff acceptance integration |

Aliases `order`, `ticket`, and `handoff` are accepted, but use the full names for clarity. For example:

```dotenv
SERVICE_TASKS_GOALS=order_status,ticket_resolution,human_handoff
```

Enable the corresponding ticket/handoff features as well. Notification and refund adapters are not in the default worker policy registry; adding `notification`, `refund_request`, `notify`, or `refund` to this list does not create a working refund or notification workflow.

To stop accepting new saved goals while keeping the worker available for existing work, use an empty list:

```dotenv
SERVICE_TASKS_GOALS=
```

To stop this task intake and worker, set `SERVICE_TASKS_ENABLED=false` and restart. Both cases leave unhandled requests on the existing message pipeline where applicable; they do not necessarily disable all synchronous order tools or ticket/handoff behavior. Neither change cancels existing records or reverses an external action already issued.

## Connect order lookup

Ask the business-system owner to provide an endpoint that understands AskFlow's authenticated customer identity. An order number alone is not proof that the caller owns the order.

```dotenv
ORDER_LOOKUP_URL=https://orders.example.com/askflow/order-status
ORDER_LOOKUP_TOKEN=REPLACE_WITH_ORDER_SERVICE_TOKEN
```

This is the **complete endpoint URL**; unlike model bases, it does not receive an automatic `/v1` suffix. The token is optional if the endpoint is deliberately configured without bearer authentication. Otherwise supply the actual service token.

The current saved-task adapter sends an HTTP GET with query parameters `order_id` and `customer_id`, and `Authorization: Bearer ...` when configured. The service must validate the customer/order relationship and return flat JSON such as:

```json
{
  "order_id": "ORD202401019999",
  "customer_id": "REPLACE_WITH_AUTHENTICATED_ASKFLOW_USER_ID",
  "status": "shipped"
}
```

These are example values; the real response must contain the requested order and authenticated customer IDs. Do not build a service that merely echoes an arbitrary customer ID without verifying ownership. The status must be concrete; missing, mock, unknown, or mismatched data does not resolve the task.

The order adapter currently has a fixed five-second HTTP timeout. `LLM_TIMEOUT_SECONDS` and connector-record `timeout_ms` do not change it. The older synchronous order tool has a different response interpretation; validate the path your deployment actually uses.

After restarting, test a valid order from a customer account, an order belonging to a different customer, and an unavailable upstream service. Refresh the conversation to read saved background results. The current UI has no task dashboard or cancel button, and background updates are not guaranteed to arrive as live chat pushes.

## Configure human support

Enable `handoff` and arrange staff roles. Add the `teams` feature if needed, then use **Admin → 技能组 (Skill groups)** to create groups and add staff. Agents without appropriate group membership see no new queued requests. The `mvp` bundle does not include `teams`; add `+teams` when using staff-scoped queues.

```dotenv
HANDOFF_TIMEOUT_SECONDS=300
SWEEPER_ENABLED=true
SWEEPER_INTERVAL_SECONDS=60
```

An unclaimed queue item older than the timeout can become a high-priority ticket and return its conversation to automated handling. The sweeper checks periodically, so the event may occur after the exact threshold. Its effective interval is at least 15 seconds. Claimed items are not timed out by the unclaimed-queue sweep.

`SWEEPER_ENABLED` controls both the periodic handoff timeout sweep and SLA scan. It does not control service-task or indexing workers. The background jobs are disabled in `ASKFLOW_ENV=test`.

Verify by requesting a person from a test customer account, claiming and replying as staff, then testing an intentionally unclaimed request separately. Use [Support staff](../user-guide/support-staff.md) for screen instructions.

## Understand SLA policy

The current service-time policies are built into the application, not editable environment settings or a browser form:

| Ticket priority | First response target | Resolution target |
| --- | --- | --- |
| `urgent` | 15 minutes | 120 minutes |
| `high` | 30 minutes | 240 minutes |
| `medium` | 120 minutes | 1,440 minutes (1 day) |
| `low` | 480 minutes | 4,320 minutes (3 days) |

Warnings begin at approximately 70% of the relevant duration. These are elapsed-time targets from ticket creation, not a business-hours calendar. Unknown priorities use the medium policy. Policy customization requires a developer/integration change; variables such as `SLA_TIMEOUT` will be ignored.

Use **Admin → SLA 监控 → 立即扫描并通知 (Scan and notify now)** to perform a manual check. It can emit notifications; it is not just refreshing the display. See the [monitoring guide](../user-guide/reports.md) for interpreting results.

## Connect notifications

A **webhook** is an HTTP address to which AskFlow sends an event. It needs a receiving application; an email address is not a webhook URL.

```dotenv
NOTIFY_WEBHOOK_URL=https://automation.example.com/askflow/events
NOTIFY_WEBHOOK_SECRET=REPLACE_WITH_A_SHARED_NOTIFICATION_SECRET
```

Enable the `notify` feature where its routes or effects are needed. The receiver and AskFlow must agree on the secret. When the separate secret is omitted, signing falls back to `SECRET_KEY`.

Events include ticket creation, handoff timeout, and SLA warning/breach where emitted by the relevant path. The request body contains `event`, `ts`, and `data`. For the receiver's developer, the signature is hexadecimal HMAC-SHA256 over `timestamp + "." + raw_body`, supplied as `X-AskFlow-Signature`; the timestamp is also in `X-AskFlow-Timestamp`.

Without a URL, events are recorded to an in-process sink and may be logged as `sent_sink`; no email or external delivery occurred. With a URL, test an intended event and confirm receipt at the destination. Failed webhook delivery does not necessarily fail the customer's chat request.

There is no SMTP setup or generic customer “send email” automation exposed by these settings. To deliver email or a messaging notification, the receiving integration must implement it. A saved preference for email does not configure that delivery.

## Manage database-backed connectors

**Admin → 业务连接器 (Business connectors)** displays connector records and a test action. Those records are separate from `ORDER_LOOKUP_URL`; changing a record called `order_status` does not configure the saved-task order adapter.

The initial `order_status` and `crm_lookup` records point to a public HTTP echo service for demonstration. Do not send real customer information to them as if they were your business systems.

There is no connector edit form. An authorized administrator/integration can use `PUT /api/v1/admin/connectors/{name}` with a complete configuration body. Example for an operator to adapt:

```json
{
  "name": "crm_lookup",
  "base_url": "https://crm.example.com",
  "method": "GET",
  "path_template": "/customers/{customer_id}",
  "auth_header": "Bearer REPLACE_WITH_CRM_TOKEN",
  "timeout_ms": 5000,
  "enabled": true,
  "description": "Customer lookup",
  "headers": {}
}
```

`timeout_ms` is milliseconds (5000 = five seconds). `auth_header` is the full Authorization header value. This update is not a partial patch: omitted fields can reset to defaults, including authentication and headers. Preserve the full intended configuration when changing one field.

Test through `POST /api/v1/admin/connectors/crm_lookup/invoke` with `{"params":{"customer_id":"APPROVED_TEST_CUSTOMER_ID"}}`. The current generic connector substitutes path placeholders and sends parameters in the URL query, even for methods other than GET; it is not a general JSON-body workflow builder. The browser's **试调用 (Test call)** sends empty parameters.

Check `status` and `data_source`: failures can return mock responses instead of raising an error. Successful registration or an echo response does not connect this record to an arbitrary chat intent. Have the operator arrange any needed workflow integration.

## Use an administrator API when no screen exists

An API is a way to send a structured request directly to AskFlow. If you are unfamiliar with it, give the endpoint and required fields above to your operator. You do not need to invent terminal commands containing secret tokens.

For a local development installation, the interactive interface at `http://localhost:8000/docs` provides a form:

1. Find the local-login operation, `POST /api/v1/admin/auth/login`, and choose **Try it out**.
2. Enter your administrator username and password in the request form and execute it privately.
3. Copy only the returned `access_token` into the page's **Authorize** bearer-token field, then authorize.
4. Find the desired operation, supply its path fields and request body, inspect them, and execute once.
5. Check the response and the relevant saved record. Sign out of the authorization dialog when finished.

Interactive operations really execute: connector calls may contact an external system, and updates change stored configuration. Use approved test records when checking connections. Keep token responses out of screenshots and support reports.

Interactive docs are disabled in staging/production. Use your organization's approved administrator API client there; do not switch a shared production installation to development merely to expose the form.

## Response rules, budgets, and preferences

Use **意图路由 (Intent routing)** and **提示词模板 (Prompt templates)** for the database-backed controls described in [Administration](../user-guide/administration.md). Enabled saved goals can be accepted before the legacy intent mapping, and current answer paths do not universally consume stored prompt templates. Saving a template cannot override authorization or guarantee changed wording in every path.

`MAX_LOOP_STEPS`, `MAX_TOOL_CALLS`, `MAX_WALL_MS`, and `MAX_RETRIES_PER_TOOL` bound the older tool loop. They are not the saved-task scheduler's complete budgets. Task deadlines/cost budgets and preference retention are not global environment settings in this version. Preference requests explicitly choose retention (default 30 days, range 1–90); see [Privacy](../user-guide/privacy.md).
