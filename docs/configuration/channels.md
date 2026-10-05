# Channels and extensions

[Configuration guide](README.md) · Next: [Verification and troubleshooting](troubleshooting.md)

Channel setup requires both AskFlow configuration and the external website or messaging platform's configuration. A loaded plugin is only one part of that setup.

## Website widget

Enable `widget`, restart the API, and have the website operator make the web route `/widget` available with working `/api` proxying. A simple embedding example for the website owner is:

```html
<iframe
  src="https://support.example.com/widget"
  title="Customer support"
  width="400"
  height="600"
></iframe>
```

Replace the example address with the actual AskFlow website. This is HTML for the host website, not a setting to paste into `.env`. The host must allow the frame and the AskFlow response headers must permit the intended embedding. Test in the browsers your visitors use.

There are no `WIDGET_*` environment settings for branding, allowed host sites, session expiry, or welcome text. The current visitor session uses a fixed two-hour guest token and browser-tab session storage. Its recorded `origin` field is not an enforced host allowlist; CORS is not a substitute for one.

Verify that an anonymous visitor can open the widget, ask a supported question, and reload the conversation in the same session. A widget visitor is not automatically linked to a normal website account. Follow-up delivery, identity verification, branding changes, and expired-session recovery may need additional integration.

## Feishu

Ask the Feishu application owner to supply the event verification token, application ID, and application secret. Enable `feishu` and add:

```dotenv
FEISHU_VERIFICATION_TOKEN=REPLACE_WITH_FEISHU_VERIFICATION_TOKEN
FEISHU_APP_ID=REPLACE_WITH_FEISHU_APP_ID
FEISHU_APP_SECRET=REPLACE_WITH_FEISHU_APP_SECRET
```

1. Restart AskFlow.
2. In the Feishu app's event settings, use your actual externally reachable HTTPS address followed by `/api/v1/channels/feishu/events`.
3. Complete the platform's URL challenge verification.
4. Subscribe to `im.message.receive_v1` and grant the relevant receive/reply permissions.
5. Send a text question through the actual bot and verify the reply in Feishu.

The application ID and secret are needed for outbound API replies. Without them, development processing may produce `reply_text` in a callback response but no message in Feishu. Text is the implemented input path; do not assume encrypted-event envelopes, attachments, or arbitrary platform modes are supported merely because URL verification passed. Have the platform operator validate the selected mode against the adapter.

Use the [Feishu integration checklist](../../deploy/checklists/feishu-channel.md) for the operator's request details.

## WeCom

Enable `wecom` and obtain the application details from its administrator:

```dotenv
WECOM_TOKEN=REPLACE_WITH_WECOM_CALLBACK_TOKEN
WECOM_CORP_ID=REPLACE_WITH_CORPORATION_ID
WECOM_AGENT_ID=REPLACE_WITH_APPLICATION_ID
```

The adapter exposes GET/POST `/api/v1/channels/wecom/events`. It currently accepts simplified JSON text events and plain/test URL verification. It is not a complete encrypted XML WeCom application callback integration.

In particular, setting `WECOM_TOKEN` does not supply complete inbound authentication for every POST: the current message handler only compares an optional body token in production-like modes. The operator must provide verified gateway handling or complete the adapter before exposing this as a trusted production message source.

`WECOM_CORP_ID` and `WECOM_AGENT_ID` are reserved for extension and are not currently used to send messages. The implementation does not provide a working outbound WeCom reply client, and production callback responses do not include the development `reply_text` field. These environment values alone cannot complete a two-way support bot.

Arrange a compatible gateway/adapter with the platform owner, verify identity and reply delivery, then share the channel with customers. See the [WeCom/DingTalk checklist](../../deploy/checklists/wecom-dingtalk-channel.md).

## DingTalk

Enable `dingtalk` and configure:

```dotenv
DINGTALK_APP_SECRET=REPLACE_WITH_DINGTALK_SIGNATURE_SECRET
DINGTALK_APP_KEY=REPLACE_WITH_DINGTALK_APPLICATION_KEY
```

The adapter accepts POST `/api/v1/channels/dingtalk/events`, verifies its supported `timestamp`/`sign` header format for message handling, and returns a text robot-response body. `DINGTALK_APP_KEY` is reserved and is not currently used to establish an outbound client.

The platform operator must confirm the callback mode matches this signing and response format. The adapter is not a general implementation of DingTalk streaming, encrypted callbacks, or asynchronous replies; timestamp freshness/replay handling also needs assessment in the actual gateway. A successful challenge response does not demonstrate authenticated message processing.

Test a real text message, a rejected invalid signature, and visible response delivery. Use the integration checklist linked above. Attachment cues can record the existence of files or pictures without extracting their contents.

## Verify later updates separately

All channels need independent tests for initial replies, human replies, and background-task outcomes. The current channel adapters do not guarantee outbound delivery of every later staff message or task update. Do not advertise complete cross-channel continuation or automatic account merging without your own verified integration.

If you are not using a channel, remove its plugin from the chosen profile/deltas and align the frontend feature list. Merely omitting credentials is not the same as disabling its inbound routes.

## Language and bot profiles

`DEFAULT_LOCALE=zh-CN` is the default. The small backend message catalog also has `en-US`; it does not translate the React interface or every hardcoded response. Saved customer preferences use their own vocabulary, including `en`, and are a separate feature.

Advanced integrations can define bot profiles:

```dotenv
DEFAULT_LOCALE=en-US
DEFAULT_BOT_ID=support
BOT_PROFILES_JSON='[{"id":"support","name":"Support","system_prompt_key":"rag.system","knowledge_tags":[],"locale":"en-US"}]'
```

The JSON is a list of objects. The loader keeps a default bot and falls back if a requested profile is absent. Malformed JSON is silently ignored rather than necessarily stopping startup, so have the operator check the bots endpoint `/api/v1/admin/bots` after restarting. That administrator endpoint requires the `ops` feature.

These profile fields do not establish separate secured knowledge collections or guarantee prompt/locale selection throughout the current chat pipeline. There is no complete multi-bot configuration screen or customer bot picker. Treat profile-based behavior as an integration that needs path-by-path verification.

## MCP, reasoning, and sandbox switches

**MCP** here exposes an extension for registering approved tool names. To use the implemented registration support, enable the `mcp` feature and set `MCP_ENABLED=true`, with a comma-separated `MCP_TOOL_WHITELIST` (default `search_knowledge`). Restart and inspect `/api/v1/admin/mcp/tools` with an administrator account.

There is no remote MCP server URL or transport configuration in this version. Unknown allowlisted names can become echo stubs, rather than real remote tools. Enabling the switch does not install an external integration.

`REASONING_ENABLED` defaults to false. When enabled, `REASONING_INTENT_WHITELIST` selects exact intent names and `REASONING_MAX_STEPS` adds steps to the older loop. The default whitelist `product_faq,troubleshoot` does not match the normal built-in intent vocabulary, so simply enabling it may have no effect. It is not a provider-specific “reasoning model” control.

`SANDBOX_ENABLED` defaults to false and only changes a gate for sandbox-prefixed tools. It does not create an isolated execution environment or install tools. Leave it false unless a developer has supplied and validated that execution environment.

## Audit export to a security system

A **SIEM** is an external system collecting security events. Set `SIEM_WEBHOOK_URL` to its approved receiving integration if your operator uses the audit export/push APIs. The value alone does not start continuous audit forwarding. There is no scheduled forwarding job or separate SIEM authentication setting in the standard configuration.

Have the receiver's operator confirm the request format and access controls and verify an explicit export/push. See the [audit endpoints](../../apps/api/app/api/v1/admin/audit_logs/routes.py) for the integration interface.
