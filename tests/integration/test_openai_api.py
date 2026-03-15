from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_v1_models_lists_two_demo_workflows(client: TestClient) -> None:
    response = client.get("/v1/models")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == ["demo_hitl", "demo_summary"]


def test_chat_completions_non_stream_summary_returns_text(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_summary",
            "messages": [{"role": "user", "content": "Summarize the launch checklist"}],
        },
        headers={"systemKey": "demo-system", "session-id": "summary-session", "user-id": "u1"},
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
        headers={"systemKey": "demo-system", "session-id": "hitl-session", "user-id": "u2"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        got_tool_call = False
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            payload = json.loads(line[6:])
            delta = payload["choices"][0]["delta"]
            if "tool_calls" in delta:
                got_tool_call = True
                break

        assert got_tool_call


def test_chat_completions_hitl_resume_returns_final_content(client: TestClient) -> None:
    first = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo_hitl",
            "messages": [{"role": "user", "content": "Write a release note"}],
        },
        headers={"systemKey": "demo-system", "session-id": "resume-session", "user-id": "u3"},
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
        headers={"systemKey": "demo-system", "session-id": "resume-session", "user-id": "u3"},
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
        headers={"systemKey": "demo-system"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert payload["error"]["code"] == "invalid_model"
