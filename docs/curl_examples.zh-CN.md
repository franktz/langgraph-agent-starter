# cURL 示例

[English](curl_examples.md)

这些示例使用 Bash 语法，并面向仓库内置的两个 demo workflow：

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

## 说明

- `model` 直接映射到 workflow 名称。
- `SYSTEMKEY` 用来选择业务系统范围；当前 demo 的上游模型配置统一放在各自 workflow 配置里的 `llm.default` 下。
- 当前仓库内置 `demo_hitl` 和 `demo_summary` 两个 workflow。
- 如果只想测试 HITL 恢复行为，请在前后两次请求中保持同一个 `session-id`。
