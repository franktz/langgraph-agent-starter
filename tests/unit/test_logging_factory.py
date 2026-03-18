import logging

from infrastructure.logging.factory import BOOTSTRAP_HANDLER_MARKER, setup_bootstrap_logging


def test_setup_bootstrap_logging_writes_to_bootstrap_log(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    try:
        setup_bootstrap_logging()
        setup_bootstrap_logging()

        logging.getLogger("tests.bootstrap").info("bootstrap-ready")

        bootstrap_log = tmp_path / "logs" / "bootstrap.log"
        assert bootstrap_log.exists()
        assert "bootstrap-ready" in bootstrap_log.read_text(encoding="utf-8")
        bootstrap_handlers = [
            handler for handler in root.handlers if getattr(handler, BOOTSTRAP_HANDLER_MARKER, False)
        ]
        assert len(bootstrap_handlers) == 1
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)
