from __future__ import annotations

import contextvars
import logging
from collections.abc import Callable
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from sys import stderr

from infrastructure.config.provider import ConfigProvider

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")
session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="-")


class TraceFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get("-")
        if not hasattr(record, "session_id"):
            record.session_id = session_id_var.get("-")
        if not hasattr(record, "trace_id"):
            record.trace_id = trace_id_var.get("-")
        return super().format(record)


class LoggerFactory:
    def get_logger(self, name: str) -> logging.LoggerAdapter[logging.Logger]:
        return logging.LoggerAdapter(logging.getLogger(name), {})

    def traced(self, request_id: str | None = None, trace_id: str | None = None) -> Callable:
        def _decorator(func: Callable) -> Callable:
            @wraps(func)
            async def _async_wrapper(*args, **kwargs):
                token1 = request_id_var.set(request_id or request_id_var.get("-"))
                token2 = session_id_var.set(trace_id or session_id_var.get("-"))
                token3 = trace_id_var.set(trace_id or trace_id_var.get("-"))
                try:
                    return await func(*args, **kwargs)
                finally:
                    request_id_var.reset(token1)
                    session_id_var.reset(token2)
                    trace_id_var.reset(token3)

            return _async_wrapper

        return _decorator


def setup_logging(config_provider: ConfigProvider) -> LoggerFactory:
    conf = config_provider.conf
    log_dir = Path(str(conf.get("logging.dir", "logs")))
    log_dir.mkdir(parents=True, exist_ok=True)
    info_path = log_dir / "info.log"
    error_path = log_dir / "error.log"
    info_path.touch(exist_ok=True)
    error_path.touch(exist_ok=True)

    formatter = TraceFormatter(
        "%(asctime)s %(levelname)s [req=%(request_id)s session=%(session_id)s trace=%(trace_id)s] %(name)s %(message)s"
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(str(conf.get("logging.level", "INFO")))

    info_handler = RotatingFileHandler(
        info_path,
        maxBytes=int(conf.get("logging.max_bytes", 104857600)),
        backupCount=int(conf.get("logging.backup_count", 7)),
        encoding="utf-8",
    )
    info_handler.setLevel(logging.DEBUG)
    info_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    info_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        error_path,
        maxBytes=int(conf.get("logging.max_bytes", 104857600)),
        backupCount=int(conf.get("logging.backup_count", 7)),
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    if bool(conf.get("logging.console_enabled", True)):
        console_handler = logging.StreamHandler(stderr)
        console_handler.setLevel(str(conf.get("logging.level", "INFO")))
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    root.addHandler(info_handler)
    root.addHandler(error_handler)
    return LoggerFactory()
