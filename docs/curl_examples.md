# cURL Examples

[Chinese Version](curl_examples.zh-CN.md)

These examples use Bash syntax and target the built-in demo workflows:

- `demo_chat`: multi-turn chat with persisted conversation history
- `demo_summary`: regular workflow without HITL
- `demo_hitl`: workflow with human-in-the-loop interrupt and resume

The default local server address in this repository is `http://127.0.0.1:8080`.

## Shared Variables

```bash
BASE_URL="http://127.0.0.1:8080"
SYSTEMKEY="demo-system"
USER_ID="tz20260315"
SESSION_ID="home20260315"
```

## List Available Workflows

```bash
curl -sS "$BASE_URL/v1/models"
```

## Call `demo_summary`

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

## Call `demo_chat` For The First Round

Use the same `session-id` and `user-id` on later rounds if you want the chat
history to continue.

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

## Continue `demo_chat` On A Later Round

For later rounds, you can send only the new user message. The workflow restores
prior history from the LangGraph checkpointer by the same identity scope.

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

## Call `demo_hitl` For The First Round

The first request pauses at the HITL review step and returns `tool_calls`.

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

## Resume `demo_hitl` With Human Confirmation

Resume must reuse the same `session-id`. Put the human-confirmed content in the
last `tool` message.

Replace `call_xxx` with the `tool_calls[0].id` returned by the first request.

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

## Stream `demo_hitl`

The streaming response emits real draft content deltas first, then
`tool_calls`, and finally `data: [DONE]`.

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

## Stream `demo_chat`

`demo_chat` also supports true SSE streaming. The server emits content deltas as
the upstream LLM returns them.

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

## Notes

- `model` maps directly to a workflow name.
- `SYSTEMKEY` identifies the caller's business system scope. The current demo
  keeps its upstream model config under `llm.default` inside each workflow
  config.
- When `api.auth.enabled` is turned on, `SYSTEMKEY` must be included in
  `api.auth.systemkeys`, otherwise the API returns `401 invalid_system_key`.
- `demo_chat` conversation history is scoped by `model + systemkey + user-id + session-id`.
- This repo currently includes `demo_chat`, `demo_hitl`, and `demo_summary`.
- If you only want to test HITL resume behavior, keep the same `session-id`
  across both requests.
