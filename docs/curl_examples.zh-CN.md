# cURL 示例

[English](curl_examples.md)

这份文档提供 Bash 写法的调用示例，覆盖仓库内置的两张演示图：

- `demo_summary`：普通总结流，不带 HITL
- `demo_hitl`：带人工审核中断与恢复的 HITL 流

本仓库默认本地地址为 `http://127.0.0.1:8080`。

## 公共变量

```bash
BASE_URL="http://127.0.0.1:8080"
SYSTEMKEY="demo-system"
USER_ID="tz20260315"
SESSION_ID="home20260315"
```

## 查看可用图

```bash
curl -sS "$BASE_URL/v1/models"
```

## 调用 `demo_summary`

```bash
curl -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_summary",
    "messages": [
      {
        "role": "user",
        "content": "请总结本周发布检查项，突出 action、risk 和 owner。"
      }
    ]
  }'
```

## 首次调用 `demo_hitl`

第一次请求会在人工审核节点中断，并返回 `tool_calls`。

```bash
curl -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_hitl",
    "messages": [
      {
        "role": "user",
        "content": "请先起草一版发布说明，包含变更摘要、影响范围和发布建议。"
      }
    ]
  }'
```

## 恢复 `demo_hitl`

恢复时必须复用同一个 `session-id`，并把人工确认后的结果放到最后一条 `tool` message 中。

把下面的 `call_xxx` 替换成首次响应里 `tool_calls[0].id` 的真实值。

```bash
curl -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_hitl",
    "messages": [
      {
        "role": "user",
        "content": "请先起草一版发布说明，包含变更摘要、影响范围和发布建议。"
      },
      {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_xxx",
            "type": "function",
            "function": {
              "name": "human_review",
              "arguments": "{\"interrupt\":{\"value\":{\"draft\":\"这里替换成首次响应中的 draft 内容\"}}}"
            }
          }
        ]
      },
      {
        "role": "tool",
        "tool_call_id": "call_xxx",
        "content": "人工审核后的最终版本：本次发布重点优化部署安全性，补充失败回滚说明，并建议灰度发布。"
      }
    ]
  }'
```

## 流式调用 `demo_hitl`

流式响应会返回 `tool_calls`，最后以 `data: [DONE]` 结束。

```bash
curl -N -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_hitl",
    "stream": true,
    "messages": [
      {
        "role": "user",
        "content": "请先起草一版发布说明，包含变更摘要、影响范围和发布建议。"
      }
    ]
  }'
```

## 说明

- `model` 直接对应 workflow 名称。
- `SYSTEMKEY` 用来选择业务系统及其对应的 LLM profile。
- 当前仓库内置两张图：`demo_hitl` 和 `demo_summary`。
- 如果要验证 HITL 恢复，前后两次请求务必保持相同的 `session-id`。
