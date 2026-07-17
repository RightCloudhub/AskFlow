# Runbook：安全与兜底常见故障

## 注入/异常请求激增

1. 看 `harness_block{reason}` / 日志 `prompt_control_request`  
2. 确认安全文案仍为代码常量（未被运营模板覆盖）  
3. 必要时收紧限流；保留样本供分析（已 mask）  

## 疑似胡编政策/价格

1. 核对是否弱检索仍调用了 generate（应为 0）  
2. 查 grounding 阈值与近期 Prompt `rag.system` 版本  
3. 回滚 Prompt；补 refusals 用例  

## 订单查询全是 mock

1. `order_webhook{status}` 是否 timeout/http_error  
2. 查 `ORDER_LOOKUP_*` 与下游健康  
3. 用户侧确认 data_source 展示正常  

## 转人工黑洞

1. `handoff_timeout` 是否在涨；清扫任务是否跑  
2. 是否建了 `handoff_timeout` 工单、会话是否回 active  
3. 摘要失败不应阻塞入队——查日志 `summary_failed`  
