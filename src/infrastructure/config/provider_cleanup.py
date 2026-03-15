from __future__ import annotations

import time
from queue import SimpleQueue
from threading import Thread
from typing import Any

from dynamic_config.provider import DynamicConfigProvider


def close_dynamic_config_provider(provider: DynamicConfigProvider | None) -> None:
    if provider is None:
        return

    backend = getattr(provider, "_nacos_backend", None)
    if backend is None:
        return

    try:
        _close_backend(backend, provider=provider)
    finally:
        setattr(provider, "_nacos_backend", None)


def _close_backend(backend: Any, *, provider: DynamicConfigProvider) -> None:
    client = getattr(backend, "_client", None)
    if client is not None:
        _close_legacy_nacos_client(client=client, provider=provider)
    if hasattr(backend, "_watch_started"):
        setattr(backend, "_watch_started", False)


def _close_legacy_nacos_client(*, client: Any, provider: DynamicConfigProvider) -> None:
    settings = provider.nacos_settings
    if settings is None:
        return

    pullers = _collect_pullers(client)
    callbacks = _collect_callbacks(client, settings.data_id, settings.group)
    for callback in callbacks:
        try:
            client.remove_config_watcher(settings.data_id, settings.group, callback, remove_all=True)
        except Exception:
            continue

    for puller in pullers:
        if isinstance(puller, Thread):
            puller.join(timeout=1.2)

    old_queue = getattr(client, "notify_queue", None)
    if old_queue is not None:
        client.notify_queue = SimpleQueue()
        try:
            old_queue.put(("__codex_shutdown__", None, None))
            time.sleep(0.05)
        except Exception:
            pass

    callback_pool = getattr(client, "callback_tread_pool", None)
    if callback_pool is not None:
        for method_name in ("close", "join", "terminate"):
            method = getattr(callback_pool, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass
        client.callback_tread_pool = None

    for attr_name, empty_value in (
        ("puller_mapping", {}),
        ("watcher_mapping", {}),
    ):
        if hasattr(client, attr_name):
            setattr(client, attr_name, empty_value)


def _collect_pullers(client: Any) -> list[Any]:
    mapping = getattr(client, "puller_mapping", None)
    if not isinstance(mapping, dict):
        return []
    pullers: list[Any] = []
    for value in mapping.values():
        if not isinstance(value, tuple) or not value:
            continue
        puller = value[0]
        if puller not in pullers:
            pullers.append(puller)
    return pullers


def _collect_callbacks(client: Any, data_id: str, group: str) -> list[Any]:
    watchers = getattr(client, "watcher_mapping", None)
    if not isinstance(watchers, dict):
        return []
    callbacks: list[Any] = []
    for cache_key, entries in watchers.items():
        if not isinstance(cache_key, str):
            continue
        if not cache_key.startswith(f"{data_id}+{group}+"):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            callback = getattr(entry, "callback", None)
            if callable(callback) and callback not in callbacks:
                callbacks.append(callback)
    return callbacks
