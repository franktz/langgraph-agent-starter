# cURL 示例

[English](curl_examples.md)

这些示例使用 Bash 语法，并面向仓库内置的 demo workflow：

- `demo_chat`：带持久化历史的多轮聊天流程
- `demo_summary`：不带 HITL 的普通流程
- `demo_hitl`：带人工介入中断与恢复的流程

本仓库默认本地服务地址为 `http://127.0.0.1:8080`。

## 共享变量

```bash
BASE_URL="http://127.0.0.1:8080"
SYSTEMKEY="demo-system"
USER_ID="tz20260315"
SESSION_ID="home20260315"
```

## 查看可用 Workflow

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
        "content": "Please summarize this week'\''s launch checklist and highlight actions, risks, and owners."
      }
    ]
  }'
```

## 首轮调用 `demo_chat`

如果你希望后续轮次延续聊天历史，请继续复用同一个 `session-id` 和 `user-id`。

```bash
curl -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_chat",
    "messages": [
      {
        "role": "user",
        "content": "Hi, please remember that my deployment window is every Friday night."
      }
    ]
  }'
```

## 后续轮次继续调用 `demo_chat`

后续轮次只传本轮新增的 user message 即可。workflow 会按同一个身份范围从 LangGraph checkpointer 恢复之前的历史。

```bash
curl -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_chat",
    "messages": [
      {
        "role": "user",
        "content": "What deployment window did I tell you earlier?"
      }
    ]
  }'
```

## 首轮调用 `demo_hitl`

第一次请求会在 HITL 审核节点暂停，并返回 `tool_calls`。

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
        "content": "Draft a release note with change summary, impact scope, and rollout advice."
      }
    ]
  }'
```

## 用人工确认结果恢复 `demo_hitl`

恢复时必须沿用同一个 `session-id`，并把人工确认后的最终内容放到最后一条 `tool` message 中。

把下面的 `call_xxx` 替换成第一次响应里 `tool_calls[0].id` 的真实值。

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
        "content": "Draft a release note with change summary, impact scope, and rollout advice."
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
              "arguments": "{\"interrupt\":{\"value\":{\"draft\":\"placeholder draft from the first response\"}}}"
            }
          }
        ]
      },
      {
        "role": "tool",
        "tool_call_id": "call_xxx",
        "content": "Human-approved final version: this release improves deployment safety, adds rollback guidance, and recommends a gradual rollout."
      }
    ]
  }'
```

## 流式调用 `demo_hitl`

流式响应会先发出真实草稿内容增量，再发出 `tool_calls`，最后以 `data: [DONE]` 结束。

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
        "content": "Draft a release note with change summary, impact scope, and rollout advice."
      }
    ]
  }'
```

## 流式调用 `demo_chat`

`demo_chat` 同样支持真 SSE 流式输出，服务端会随着上游 LLM 返回内容持续发出增量 chunk。

```bash
curl -N -sS -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "SYSTEMKEY: $SYSTEMKEY" \
  -H "user-id: $USER_ID" \
  -H "session-id: $SESSION_ID" \
  -d '{
    "model": "demo_chat",
    "stream": true,
    "messages": [
      {
        "role": "user",
        "content": "Explain the rollback plan in a concise way."
      }
    ]
  }'
```

## 说明

- `model` 直接映射到 workflow 名称。
- `SYSTEMKEY` 用来标识调用方所属的业务系统范围；当前 demo 的上游模型配置统一放在各自 workflow 配置里的 `llm.default` 下。
- 当开启 `api.auth.enabled` 时，`SYSTEMKEY` 必须命中 `api.auth.systemkeys` 白名单，否则接口会返回 `401 invalid_system_key`。
- `demo_chat` 的对话历史会按 `model + systemkey + user-id + session-id` 这个组合范围隔离。
- 当前仓库内置 `demo_chat`、`demo_hitl` 和 `demo_summary` 三个 workflow。
- 如果只想测试 HITL 恢复行为，请在前后两次请求中保持同一个 `session-id`。
