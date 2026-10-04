# 模型与答案质量

[配置指南](README.md) · 下一篇：[存储与索引](storage.md)

语言模型根据 AskFlow 提供的上下文撰写答案。嵌入模型将文本转换为数字列表，以便找到相似的段落。这是两种不同的工作，可能使用不同的服务。

## 在不连接模型的情况下开始

不设置 `LLM_BASE_URL`、`LLM_API_KEY`、`EMBEDDING_BASE_URL` 和 `EMBEDDING_API_KEY`，即可使用离线嵌入和抽取式答案。你仍然需要有用的来源文档。上传模型密钥无法提供缺失的业务知识。

要完全恢复到离线运行，请移除所有四个连接设置并重启。如果嵌入方法发生变化，请按下文所述重建搜索索引；不要混用旧向量和新向量。

## 收集连接详情

向你的模型服务提供商或组织的运维人员索取：

- 兼容的服务基础地址。
- 可使用所需服务的 API 密钥。
- 确切的对话模型标识符和嵌入模型标识符。
- 嵌入模型的输出维度，即其数字列表的长度。
- 确认支持流式对话补全和嵌入。

AskFlow 当前使用 OpenAI 兼容的对话补全（chat-completions）和嵌入协议。提供商的网站 URL、浏览器对话账号或无关的 API 都不是替代品。支持对话但不支持嵌入的服务需要单独的嵌入连接。

## 设置连接值

将以下内容添加到 API 的 `.env` 中，替换所有占位符：

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

维度 `384` 是与离线默认值匹配的示例，不是通用的嵌入大小。请将其设置为提供商实际的输出维度。

**两个基础 URL 都不要包含结尾的 `/v1`。** 当前客户端会自行追加 `/v1/chat/completions` 和 `/v1/embeddings`。例如，`https://models.example.com` 会生成 `https://models.example.com/v1/chat/completions`。以 `/v1` 结尾的基础地址会生成 `/v1/v1/...`。仓库 `.env.example` 中较旧的注释值并不反映此客户端行为。

如果你的网关使用额外的路径前缀，请安排一个基础地址，使其追加后的路径能到达网关的实际端点。不要把完整的 chat-completions URL 放入 `LLM_BASE_URL`。

客户端需要同时具备地址和非空密钥才被视为已配置。如果本地网关有不同的认证要求，请让运维人员确认兼容性，而不要猜测凭据。

## 理解嵌入回退

当省略 `EMBEDDING_BASE_URL` 时，AskFlow 使用 `LLM_BASE_URL`。当省略 `EMBEDDING_API_KEY` 时，它使用 `LLM_API_KEY`。每个回退都是独立的。

因此，添加对话模型连接也可能将文档和查询嵌入从离线切换到远程。空的嵌入字段无法可靠地保持嵌入离线，因为回退仍然适用。如果你需要远程对话但严格离线嵌入，当前环境设置没有为这种组合提供专用开关。

如果使用不同的提供商，请**同时**设置两个嵌入连接值，以免嵌入地址无意中收到对话提供商的密钥。嵌入客户端会发送模型和文本，但不会发送将向量调整为 `EMBEDDING_DIM` 的请求；请将该字段配置为与提供商实际返回的内容匹配。

## 按用途选择模型

| 设置 | 默认值 | 当前用途 |
| --- | --- | --- |
| `LLM_MODEL_GENERATE` | `gpt-4o-mini` | 主知识答案模型 |
| `LLM_MODEL_CLASSIFY` | `gpt-4o-mini` | 模型路由分类选择和回退候选；默认分类器仍基于规则 |
| `LLM_MODEL_REWRITE` | `gpt-4o-mini` | 模型路由改写选择；常规查询改写使用同义词规则 |
| `LLM_MODEL_SUMMARY` | `gpt-4o-mini` | 摘要/草稿辅助模型选择，以及使用路由时的回退候选 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 远程嵌入模型；离线运行使用 `offline-hash` |

这些是仓库默认值，不是关于当前提供商可用性或定价的建议。请使用你的服务支持的 ID。更改模型设置不会把每个基于规则的操作都变成模型调用。

回退行为也因路径而异。路由器有一个代码定义的候选链；它不能作为 `.env` 中的逐提供商列表进行配置。主流式知识生成使用其选定的模型，并在失败时回退到抽取式文本。不要假设每个失败的请求都会自动切换到第二个托管模型。

## 应用并验证

1. 保存连接值并重启 API。
2. 如果嵌入方法、模型或维度发生变化，请在判断答案质量之前将文档重建为兼容的搜索索引。
3. 上传一个小型可读的文本文档，或让运维人员为现有文档重建索引。
4. 提出一个答案在该文档中的问题。
5. 检查引用，并查看运维人员的模型请求日志或提供商用量，以确认调用了预期的服务。
6. 检查一个文档无法回答的问题；AskFlow 仍应能够拒答。

收到可读的响应本身并不证明模型连接成功：答案可能是抽取式回退。`/health` 不会测试模型凭据或提供商可用性。

更改嵌入模型需要使用相同的新嵌入方法为所有相关文档重建索引。对于 Chroma，当维度或模型变化时，请使用单独的兼容集合。保留旧配置和索引，直到新设置经过验证。仅恢复模型名称无法修复混合索引。

## 谨慎调整搜索和答案限制

在你拥有有代表性的问题和已知的正确结果之前，请保持默认值。

| 设置 | 默认值 | 更改它的含义 |
| --- | --- | --- |
| `GROUNDING_THRESHOLD` | `0.35` | 更高要求更强的搜索证据；更低允许更弱的匹配 |
| `GROUNDING_MIN_HITS` | `1` | 回答所需的最少可用搜索结果数量 |
| `GROUNDING_WEAK_SOURCES` | `2` | 在证据不足响应中返回的弱引用段落的最大数量 |
| `MAX_QUESTION_CHARS` | `2000` | 客户问题的限制 |
| `MAX_ANSWER_CHARS` | `4000` | 答案长度限制；在当前生成器中也会作为模型的 `max_tokens` 值提供，尽管单位不同 |
| `MAX_HISTORY_MESSAGES` | `20` | 处理请求时考虑的较早消息数量的界限 |
| `MAX_HISTORY_CHARS` | `6000` | 包含的较早文本总量的界限 |
| `HISTORY_SUMMARY_THRESHOLD` | `12` | 当消息数量超过此值时压缩较早的历史 |
| `HISTORY_SUMMARY_KEEP_RECENT` | `4` | 在摘要旁保留的最近消息数量 |
| `RETRIEVAL_CACHE_TTL_S` | `60` | 复用缓存搜索结果的秒数；`0` 禁用缓存 |
| `RETRIEVAL_CACHE_MAX_ENTRIES` | `256` | 每个进程缓存结果条目的最大值 |

这些限制影响响应上下文，而不是记录存储的时长。降低证据阈值并不能纠正缺失或糟糕的文档。每次更改后测试可回答和不可回答的问题，如果错误答案增加，请恢复先前的值。

在内容维护后，缓存的搜索结果可能暂时保留旧段落。请等待配置的缓存生命周期结束，或让运维人员刷新相关进程和索引，然后再验证更正。

## 添加同义词

`REWRITE_SYNONYM_PATH` 指向一个包含等价搜索词的 YAML 文本文件。从 `apps/api` 运行时默认值为 `../../data/samples/query_synonyms.yaml`。对于组织特定的文件，请使用清晰的绝对路径：

```dotenv
REWRITE_SYNONYM_PATH=/srv/askflow/config/query-synonyms.yaml
```

示例文件内容：

```yaml
groups:
  - canonical: returns
    aliases:
      - return policy
      - send an item back
```

使用空格进行缩进。添加你文档中使用的真正等价词，保存文件，并重启 API 以便可预测地采用。同时询问原始措辞和一个别名，然后检查它们是否检索到合适的材料。文件缺失会导致没有加载任何同义词组；格式错误的 YAML 可能导致失败。保留你上一个可用的文件，以便可以恢复。
