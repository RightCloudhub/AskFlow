# Runbook：性能与记忆

## TTFT 变慢

1. 分 purpose 看 `llm_latency` vs `retrieval_latency`  
2. 是否误开 LLM 改写 / 历史未裁剪（`history.used_count`）  
3. chunk 数是否被调大；先减上下文再换模型  

## Token / 费用飙升

1. 拒答率是否异常下降（可能在瞎答）  
2. classify 是否每轮都打大模型  
3. 检查 max_tokens 与重复重试  

## 长会话答非所问

1. 是否裁掉关键 staff 结论（镜像与条数）  
2. 槽位是否错误保留/丢弃  
3. 引导用户新开会话或（后续）开摘要压缩  

## 索引积压导致「记不住新知识」

1. `index_queue_depth`、最老 pending 年龄  
2. worker 是否存活；failed 文档错误信息  
3. 知识在 M3，与会话 M1 无关——勿在对话层「硬记」新政策  
