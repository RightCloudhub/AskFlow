# Models and answer quality

[Configuration guide](README.md) · Next: [Storage and indexing](storage.md)

A language model writes answers from the context AskFlow supplies. An embedding model converts text into number lists so similar passages can be found. These are different jobs and may use different services.

## Start without a model connection

Leave `LLM_BASE_URL`, `LLM_API_KEY`, `EMBEDDING_BASE_URL`, and `EMBEDDING_API_KEY` unset to use offline embeddings and extractive answers. You still need useful source documents. Uploading a model key cannot supply missing business knowledge.

To return completely to offline operation, remove all four connection settings and restart. If the embedding method changes, rebuild the search index as described below; do not mix old and new vectors.

## Gather connection details

Ask your model-service provider or organization's operator for:

- A compatible service base address.
- An API key that can use the requested services.
- The exact chat model identifier and embedding model identifier.
- The embedding model's output dimension, meaning the length of its number list.
- Confirmation that streaming chat completions and embeddings are supported.

AskFlow currently uses an OpenAI-compatible chat-completions and embeddings protocol. A provider's website URL, browser-chat account, or unrelated API is not a substitute. A service supporting chat but not embeddings needs a separate embedding connection.

## Set connection values

Add the following to the API `.env`, replacing every placeholder:

```dotenv
LLM_BASE_URL=https://models.example.com
LLM_API_KEY=REPLACE_WITH_PROVIDER_KEY
LLM_MODEL_GENERATE=REPLACE_WITH_CHAT_MODEL_ID
EMBEDDING_BASE_URL=https://embeddings.example.com
EMBEDDING_API_KEY=REPLACE_WITH_EMBEDDING_KEY
EMBEDDING_MODEL=REPLACE_WITH_EMBEDDING_MODEL_ID
EMBEDDING_DIM=384
LLM_TIMEOUT_SECONDS=60
```

The dimension `384` is an example matching the offline default, not a universal embedding size. Set it to the actual provider output dimension.

**Do not include a trailing `/v1` in either base URL.** The current clients append `/v1/chat/completions` and `/v1/embeddings` themselves. For example, `https://models.example.com` produces `https://models.example.com/v1/chat/completions`. A base ending in `/v1` would produce `/v1/v1/...`. The older commented value in the repository's `.env.example` does not reflect this client behavior.

If your gateway uses an extra path prefix, arrange a base whose appended path reaches the gateway's actual endpoint. Do not put the full chat-completions URL into `LLM_BASE_URL`.

The client needs both an address and a nonempty key to be considered configured. If a local gateway has different authentication requirements, have its operator confirm compatibility rather than guessing a credential.

## Understand embedding fallback

When `EMBEDDING_BASE_URL` is omitted, AskFlow uses `LLM_BASE_URL`. When `EMBEDDING_API_KEY` is omitted, it uses `LLM_API_KEY`. Each fallback is independent.

Therefore, adding a chat-model connection can also switch document and query embedding from offline to remote. Empty embedding fields do not reliably keep embedding offline because the fallback still applies. If you need remote chat with strictly offline embedding, the current environment settings do not provide a dedicated switch for that combination.

If using separate providers, set **both** embedding connection values so the embedding address does not inadvertently receive the chat provider's key. The embedding client sends the model and text, but does not send a request to resize the vector to `EMBEDDING_DIM`; configure that field to match what the provider actually returns.

## Choose models by purpose

| Setting | Default | Current use |
| --- | --- | --- |
| `LLM_MODEL_GENERATE` | `gpt-4o-mini` | Main knowledge-answer model |
| `LLM_MODEL_CLASSIFY` | `gpt-4o-mini` | Model-router classification selection and fallback candidates; the default classifier remains rule-based |
| `LLM_MODEL_REWRITE` | `gpt-4o-mini` | Model-router rewrite selection; normal query rewriting uses synonym rules |
| `LLM_MODEL_SUMMARY` | `gpt-4o-mini` | Summary/draft-assist model selection and fallback candidates where the router is used |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Remote embedding model; offline operation uses `offline-hash` |

These are repository defaults, not recommendations about current provider availability or pricing. Use IDs your service supports. Changing a model setting does not turn every rule-based operation into a model call.

Fallback behavior also varies by path. The router has a code-defined candidate chain; it is not configurable as a per-provider list in `.env`. Main streamed knowledge generation uses its selected model and falls back to extractive text on failure. Do not assume that every failed request automatically switches to a second hosted model.

## Apply and verify

1. Save the connection values and restart the API.
2. If the embedding method, model, or dimension changed, rebuild documents into a compatible search index before judging answer quality.
3. Upload a small readable text document, or have the operator reindex an existing one.
4. Ask a question whose answer is in that document.
5. Check citations and review the operator's model request logs or provider usage to confirm the intended service was called.
6. Check a question that the documents do not answer; AskFlow should still be able to decline it.

Receiving a readable response is not by itself proof that the model connection worked: the answer may be an extractive fallback. `/health` does not test model credentials or provider availability.

Changing embedding models requires reindexing all relevant documents with the same new embedding method. For Chroma, use a separate compatible collection when dimensions or models change. Keep the old configuration and index until the new setup is verified. Restoring a model name alone cannot repair a mixed index.

## Tune search and answer limits carefully

Keep defaults until you have representative questions and known correct outcomes.

| Setting | Default | What changing it means |
| --- | --- | --- |
| `GROUNDING_THRESHOLD` | `0.35` | Higher requires stronger search evidence; lower admits weaker matches |
| `GROUNDING_MIN_HITS` | `1` | Minimum number of usable search results needed to answer |
| `GROUNDING_WEAK_SOURCES` | `2` | Maximum weak reference passages returned with an insufficient-evidence response |
| `MAX_QUESTION_CHARS` | `2000` | Limit on a customer's question |
| `MAX_ANSWER_CHARS` | `4000` | Answer length limit; also supplied as the model's `max_tokens` value in the current generator, despite the different units |
| `MAX_HISTORY_MESSAGES` | `20` | Bounds earlier messages considered in handling a request |
| `MAX_HISTORY_CHARS` | `6000` | Bounds total earlier text included |
| `HISTORY_SUMMARY_THRESHOLD` | `12` | Compress earlier history once the message count exceeds this value |
| `HISTORY_SUMMARY_KEEP_RECENT` | `4` | Keep this many recent messages alongside the summary |
| `RETRIEVAL_CACHE_TTL_S` | `60` | Seconds to reuse cached search results; `0` disables caching |
| `RETRIEVAL_CACHE_MAX_ENTRIES` | `256` | Maximum cached result entries per process |

These limits affect response context, not how long records are stored. Lowering an evidence threshold does not correct missing or bad documents. Test both answerable and unanswerable questions after each change, then restore previous values if incorrect answers increase.

Cached search results may temporarily preserve old passages after content maintenance. Allow the configured cache lifetime to elapse or have the operator refresh the relevant processes and indexes before validating a correction.

## Add synonyms

`REWRITE_SYNONYM_PATH` points to a YAML text file of equivalent search terms. The default is `../../data/samples/query_synonyms.yaml` when running from `apps/api`. For an organization-specific file, use a clear absolute path:

```dotenv
REWRITE_SYNONYM_PATH=/srv/askflow/config/query-synonyms.yaml
```

Example file contents:

```yaml
groups:
  - canonical: returns
    aliases:
      - return policy
      - send an item back
```

Use spaces for indentation. Add genuine equivalents used in your documents, save the file, and restart the API for predictable adoption. Ask both the original wording and an alias, then check that they retrieve appropriate material. A missing file leaves no loaded synonym groups; malformed YAML can cause failures. Keep your last working file so you can restore it.
