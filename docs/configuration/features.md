# Features and the web interface

[Configuration guide](README.md) · Next: [Models and answer quality](models.md)

A **profile** is a bundle of features. A **plugin** is an individual feature such as tickets or knowledge search. Profile names describe bundles, not installation quality or a guarantee of production readiness.

## Choose a backend profile

Set `ASKFLOW_PROFILE` in the API environment and restart it:

| Profile | Included features |
| --- | --- |
| `core-only` | Core accounts, conversations, and basic administration; no knowledge-search plugin |
| `faq-only` | Core plus knowledge search and document management |
| `mvp` | Core, knowledge search, agent, tools, tickets, handoff, knowledge drafts/gaps, operational settings, costs, widget |
| `enterprise` | `mvp` plus SLA, notifications, SSO, teams, connectors, launch cards, analytics, MCP, Feishu, quality checks |
| `full` | `enterprise` plus WeCom and DingTalk; the default |

For a simple information-only service:

```dotenv
ASKFLOW_PROFILE=faq-only
SERVICE_TASKS_ENABLED=false
```

For the broader support workspace:

```dotenv
ASKFLOW_PROFILE=full
```

A profile enables code and routes. It does not provide model credentials, connect an order system, create support staff, or configure a messaging bot.

## Add or remove selected features

`ASKFLOW_FEATURES` changes the selected profile. Prefix a feature with `+` to add it or `-` to remove it:

```dotenv
ASKFLOW_PROFILE=mvp
ASKFLOW_FEATURES=+teams,+notify,-mcp
```

Dependencies are added automatically. For example, `teams` requires `handoff`, and `sla` requires `ticket`. Removing a required dependency does not remove everything that uses it: it can be added back. Remove the dependent features too when necessary, then inspect the final loaded list.

This matters when disabling exposure to a service. Do not infer the effective feature list only from a `-feature` entry.

| Feature IDs | Plain meaning |
| --- | --- |
| `core`, `rag`, `agent`, `tools` | Core, knowledge search, request handling, tool support |
| `ticket`, `handoff`, `teams` | Tickets, human support, staff groups |
| `knowledge`, `ops` | Knowledge gap/draft workflow and response configuration |
| `cost`, `analytics`, `qc`, `launch` | Cost reporting, operations reporting, quality, change records |
| `sla`, `notify` | Service-time checks and notifications |
| `sso`, `connectors`, `mcp` | Company sign-in, business connectors, tool-registration extension |
| `widget`, `feishu`, `wecom`, `dingtalk` | Customer contact channels |

The exact bundles and dependencies are in [features.yaml](../../packages/contracts/features.yaml). An unknown selected profile or feature prevents startup. Use the IDs above, not translated menu labels.

## Keep the web app in sync

The browser can discover features from the backend, but the current discovery endpoint requires a staff or administrator account. Discovery is attempted when the app loads. If it fails, the interface shows only core features. An ordinary customer may consequently miss the tickets link even when the backend supports tickets.

For a deployment with ordinary customer accounts, supply a matching, non-secret list in `apps/web/.env.local` or the web build environment. This is a **complete list**, not a `+`/`-` adjustment and not a profile name.

For `faq-only`:

```dotenv
VITE_ASKFLOW_FEATURES=core,rag
```

For `mvp` plus `teams` and `notify`:

```dotenv
VITE_ASKFLOW_FEATURES=core,rag,agent,tools,ticket,handoff,knowledge,ops,cost,widget,teams,notify
```

Restart `npm run dev` after editing the development web environment. For an already built web app, run `npm run build` in `apps/web` and have the operator publish the new `dist` output. Changing an API environment variable cannot modify an already built web bundle.

The web list only controls visible navigation and routes. Backend authorization still applies, so some staff or admin pages can be visible to an account that cannot use them. A backend-disabled feature cannot be enabled through this list.

If using automatic discovery with an administrator account, reload after signing in. To return to automatic discovery, remove `VITE_ASKFLOW_FEATURES` and restart or rebuild the web app.

## Verify and undo

1. Restart the API after changing its profile or feature list.
2. Open **Admin → 插件与能力 (Plugins and capabilities)** with a staff/admin account.
3. Check **Profile**, **启用 (Enabled)**, and **已加载 (Loaded)**.
4. Update the web list if you use an override, then restart/rebuild the web app.
5. Test the actual customer action, such as opening and creating a ticket.

This management page is read-only. To undo a change, restore the previous environment values and repeat the restart/rebuild procedure. Hiding a task-related feature does not cancel previously accepted work.
