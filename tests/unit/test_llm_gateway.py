from infrastructure.config.provider import ConfigProvider
from infrastructure.llm.gateway import LlmGateway
from infrastructure.logging.factory import setup_logging


def _build_gateway() -> LlmGateway:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    logger_factory = setup_logging(provider)
    return LlmGateway(
        logger_factory=logger_factory,
        http_client=object(),  # type: ignore[arg-type]
    )


def test_llm_gateway_build_headers_applies_apikey_and_defaults() -> None:
    gateway = _build_gateway()

    headers = gateway._build_headers(  # type: ignore[attr-defined]
        llm_config={"apikey": "secret-token"},
        systemkey="demo-system",
    )

    assert headers["Content-Type"] == "application/json"
    assert headers["X-System-Key"] == "demo-system"
    assert headers["Authorization"] == "Bearer secret-token"


def test_llm_gateway_build_headers_merges_optional_headers() -> None:
    gateway = _build_gateway()

    headers = gateway._build_headers(  # type: ignore[attr-defined]
        llm_config={"headers": {"X-Tenant": "tenant-a"}},
        systemkey="demo-system",
    )

    assert headers["Content-Type"] == "application/json"
    assert headers["X-System-Key"] == "demo-system"
    assert headers["X-Tenant"] == "tenant-a"
    assert "Authorization" not in headers
