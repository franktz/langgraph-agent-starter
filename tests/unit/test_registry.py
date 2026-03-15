from workflows.registry import WorkflowRegistry


def test_registry_exposes_demo_graphs() -> None:
    registry = WorkflowRegistry()
    assert [spec.name for spec in registry.list_specs()] == ["demo_chat", "demo_hitl", "demo_summary"]
