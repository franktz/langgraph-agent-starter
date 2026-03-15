from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_v1_models_lists_demo_workflows(client: TestClient) -> None:
    response = client.get("/v1/models")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == ["demo_chat", "demo_hitl", "demo_summary"]


def test_chat_completions_non_stream_summary_returns_text(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_summary",
            "messages": [{"role": "user", "content": "Summarize the launch checklist"}],
        },
        headers={"systemkey": "demo-system", "session-id": "summary-session", "user-id": "u1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "demo_summary"
    assert payload["choices"][0]["finish_reason"] == "stop"
    assert payload["choices"][0]["message"]["content"]
    assert "[Nacos Summary Template Updated] Dynamic config is live:" in payload["choices"][0]["message"]["content"]
    assert payload["usage"]["prompt_tokens"] > 0
    assert payload["usage"]["total_tokens"] >= payload["usage"]["prompt_tokens"]


def test_chat_completions_stream_hitl_returns_tool_call(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "demo_hitl",
            "messages": [{"role": "user", "content": "Write a release note"}],
            "stream": True,
        },
        headers={"systemkey": "demo-system", "session-id": "hitl-session", "user-id": "u2"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        got_content_delta = False
        got_tool_call = False
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            payload = json.loads(line[6:])
            delta = payload["choices"][0]["delta"]
            if delta.get("content"):
                got_content_delta = True
            if "tool_calls" in delta:
                got_tool_call = True
                break

        assert got_content_delta
        assert got_tool_call


def test_chat_completions_stream_summary_returns_multiple_content_chunks(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "demo_summary",
            "messages": [{"role": "user", "content": "Summarize the launch checklist"}],
            "stream": True,
        },
        headers={"systemkey": "demo-system", "session-id": "summary-stream-session", "user-id": "u4"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        content_chunks: list[str] = []
        finish_reason = None
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            payload = json.loads(line[6:])
            choice = payload["choices"][0]
            delta = choice["delta"]
            if delta.get("content"):
                content_chunks.append(delta["content"])
            if choice["finish_reason"] is not None:
                finish_reason = choice["finish_reason"]

        assert len(content_chunks) > 1
        assert "".join(content_chunks)
        assert finish_reason == "stop"


def test_chat_completions_non_stream_chat_supports_multi_turn_history(client: TestClient) -> None:
    first = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [{"role": "user", "content": "Hello there"}],
        },
        headers={"systemkey": "demo-system", "session-id": "chat-session", "user-id": "chat-user"},
    )

    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["choices"][0]["message"]["content"] == "[demo-system/mock-chat] Hello there"

    second = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [{"role": "user", "content": "What did I just say?"}],
        },
        headers={"systemkey": "demo-system", "session-id": "chat-session", "user-id": "chat-user"},
    )

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["choices"][0]["finish_reason"] == "stop"
    assert second_payload["choices"][0]["message"]["content"] == (
        "[demo-system/mock-chat] What did I just say? (history_users=1)"
    )


def test_chat_completions_chat_reuses_persisted_answer_for_replayed_history(client: TestClient) -> None:
    first = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [{"role": "user", "content": "Replay-safe question"}],
        },
        headers={"systemkey": "demo-system", "session-id": "chat-replay-session", "user-id": "chat-user"},
    )

    assert first.status_code == 200
    assistant_message = first.json()["choices"][0]["message"]["content"]

    replay = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [
                {"role": "user", "content": "Replay-safe question"},
                {"role": "assistant", "content": assistant_message},
            ],
        },
        headers={"systemkey": "demo-system", "session-id": "chat-replay-session", "user-id": "chat-user"},
    )

    assert replay.status_code == 200
    assert replay.json()["choices"][0]["message"]["content"] == assistant_message


def test_chat_completions_chat_history_isolated_by_user_and_workflow(client: TestClient) -> None:
    warmup = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [{"role": "user", "content": "Remember me"}],
        },
        headers={"systemkey": "demo-system", "session-id": "shared-session", "user-id": "user-a"},
    )
    assert warmup.status_code == 200

    different_user = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [{"role": "user", "content": "Do you have prior context?"}],
        },
        headers={"systemkey": "demo-system", "session-id": "shared-session", "user-id": "user-b"},
    )

    assert different_user.status_code == 200
    assert different_user.json()["choices"][0]["message"]["content"] == (
        "[demo-system/mock-chat] Do you have prior context?"
    )

    different_workflow = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_summary",
            "messages": [{"role": "user", "content": "Same session, different workflow"}],
        },
        headers={"systemkey": "demo-system", "session-id": "shared-session", "user-id": "user-a"},
    )

    assert different_workflow.status_code == 200
    assert different_workflow.json()["model"] == "demo_summary"


def test_chat_completions_stream_chat_returns_multiple_content_chunks(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "demo_chat",
            "messages": [{"role": "user", "content": "Stream this answer"}],
            "stream": True,
        },
        headers={"systemkey": "demo-system", "session-id": "chat-stream-session", "user-id": "chat-user"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        content_chunks: list[str] = []
        finish_reason = None
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            payload = json.loads(line[6:])
            choice = payload["choices"][0]
            delta = choice["delta"]
            if delta.get("content"):
                content_chunks.append(delta["content"])
            if choice["finish_reason"] is not None:
                finish_reason = choice["finish_reason"]

        assert len(content_chunks) > 1
        assert "".join(content_chunks) == "[demo-system/mock-chat] Stream this answer"
        assert finish_reason == "stop"


def test_chat_completions_hitl_resume_returns_final_content(client: TestClient) -> None:
    first = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_hitl",
            "messages": [{"role": "user", "content": "Write a release note"}],
        },
        headers={"systemkey": "demo-system", "session-id": "resume-session", "user-id": "u3"},
    )
    assert first.status_code == 200
    tool_call = first.json()["choices"][0]["message"]["tool_calls"][0]
    tool_args = json.loads(tool_call["function"]["arguments"])
    assert "[Nacos HITL Template] Please produce a release-ready draft before human review." in json.dumps(
        tool_args,
        ensure_ascii=False,
    )

    second = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_hitl",
            "messages": [
                {"role": "user", "content": "Write a release note"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call],
                },
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": "This release adds safer deploy handling.",
                },
            ],
        },
        headers={"systemkey": "demo-system", "session-id": "resume-session", "user-id": "u3"},
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["choices"][0]["finish_reason"] == "stop"
    assert "safer deploy handling" in payload["choices"][0]["message"]["content"]
    assert payload["usage"]["completion_tokens"] > 0


def test_chat_completions_rejects_unknown_model(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "missing-workflow",
            "messages": [{"role": "user", "content": "hello"}],
        },
        headers={"systemkey": "demo-system"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert payload["error"]["code"] == "invalid_model"


def test_chat_completions_rejects_missing_model(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "hello"}],
        },
        headers={"systemkey": "demo-system"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert payload["error"]["code"] == "missing_model"


def test_chat_completions_rejects_unauthorized_systemkey(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_summary",
            "messages": [{"role": "user", "content": "hello"}],
        },
        headers={"systemkey": "unknown-system"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["type"] == "authentication_error"
    assert payload["error"]["code"] == "invalid_system_key"


def test_chat_completions_rejects_missing_systemkey_when_auth_enabled(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_summary",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["type"] == "authentication_error"
    assert payload["error"]["code"] == "invalid_system_key"
