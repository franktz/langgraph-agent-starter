# cURL Examples

[中文版本](curl_examples.zh-CN.md)

These examples use Bash syntax and target the two built-in demo workflows:

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

Resume must reuse the same `session-id`. Put the human-confirmed content in the last `tool` message.

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

The streaming response emits `tool_calls` and finishes with `data: [DONE]`.

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

## Notes

- `model` maps directly to a workflow name.
- `SYSTEMKEY` selects the business system and its LLM profile.
- This repo currently includes `demo_hitl` and `demo_summary`.
- If you only want to test HITL resume behavior, keep the same `session-id` across both requests.
