from workflows.common.input_messages import last_text_from_input_messages


def test_last_tool_or_user_text_defaults_to_tool_and_user() -> None:
    messages = [
        {"role": "user", "content": "first user"},
        {"role": "assistant", "content": "assistant reply"},
        {"role": "tool", "content": "tool result"},
    ]

    assert last_text_from_input_messages(messages) == "tool result"


def test_last_tool_or_user_text_accepts_single_role() -> None:
    messages = [
        {"role": "user", "content": "first user"},
        {"role": "tool", "content": "tool result"},
    ]

    assert last_text_from_input_messages(messages, "user") == "first user"
    assert last_text_from_input_messages(messages, "tool") == "tool result"


def test_last_tool_or_user_text_accepts_role_collection() -> None:
    messages = [
        {"role": "user", "content": "first user"},
        {"role": "assistant", "content": "assistant reply"},
        {"role": "tool", "content": [{"type": "text", "text": "tool text"}]},
    ]

    assert last_text_from_input_messages(messages, {"tool", "user"}) == "tool text"
    assert last_text_from_input_messages(messages, {"assistant"}) == "assistant reply"
