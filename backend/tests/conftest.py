from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SEC_API_KEY", "test-sec-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ENABLE_AGENTS", "false")
os.environ.setdefault("AGENT_FALLBACK_ENABLED", "true")


def _register_module(name: str, module: types.ModuleType) -> None:
    parts = name.split(".")
    for index in range(1, len(parts)):
        package_name = ".".join(parts[:index])
        if package_name not in sys.modules:
            parent = types.ModuleType(package_name)
            package_path = BACKEND_DIR.joinpath(*parts[:index])
            if package_path.exists():
                parent.__path__ = [str(package_path)]  # type: ignore[attr-defined]
            else:
                parent.__path__ = []  # type: ignore[attr-defined]
            sys.modules[package_name] = parent
            if index > 1:
                grandparent_name = ".".join(parts[: index - 1])
                setattr(sys.modules[grandparent_name], parts[index - 1], parent)
    sys.modules[name] = module
    if len(parts) > 1:
        parent_name = ".".join(parts[:-1])
        setattr(sys.modules[parent_name], parts[-1], module)


def _install_import_stubs() -> None:
    mysql_module = types.ModuleType("mysql")
    mysql_connector_module = types.ModuleType("mysql.connector")
    mysql_connector_module.connect = lambda *args, **kwargs: MagicMock()
    mysql_module.connector = mysql_connector_module
    _register_module("mysql", mysql_module)
    _register_module("mysql.connector", mysql_connector_module)

    finance_module = types.ModuleType("api_endpoints.financeGPT.chatbot_endpoints")

    class _RemoteCallable:
        def __call__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def remote(self, *args: Any, **kwargs: Any) -> None:
            return None

    finance_module.add_chat_to_db = lambda *args, **kwargs: 1
    finance_module.add_message_to_db = lambda *args, **kwargs: 1
    finance_module.chunk_document = _RemoteCallable()
    finance_module.add_document_to_db = lambda *args, **kwargs: (1, False)
    finance_module.get_relevant_chunks = lambda *args, **kwargs: [("chunk", "doc", 1)]
    finance_module.serialize_sources_for_api = lambda sources: [
        {
            "id": source.get("id", f"source-{index}") if isinstance(source, dict) else f"source-{index}",
            "document_name": source.get("document_name", "Unknown document") if isinstance(source, dict) else source[1],
            "chunk_text": source.get("chunk_text", "") if isinstance(source, dict) else source[0],
            "page_number": source.get("page_number") if isinstance(source, dict) else (source[2] if len(source) > 2 else None),
            "start_index": source.get("start_index") if isinstance(source, dict) else (source[3] if len(source) > 3 else None),
            "end_index": source.get("end_index") if isinstance(source, dict) else (source[4] if len(source) > 4 else None),
            "source_type": source.get("source_type", "document_chunk") if isinstance(source, dict) else "document_chunk",
        }
        for index, source in enumerate(sources or [])
    ]
    finance_module.sources_to_prompt_context = lambda sources: " ".join(str(source) for source in (sources or []))
    finance_module.create_chat_shareable_url = lambda chat_id: f"/playbook/{chat_id}"
    finance_module.access_sharable_chat = lambda playbook_url: {"url": playbook_url}
    finance_module._get_model = lambda: None
    finance_module.add_sources_to_db = lambda *args, **kwargs: None
    finance_module.add_model_key_to_db = lambda *args, **kwargs: None
    finance_module.ensure_SDK_user_exists = lambda *args, **kwargs: 1
    finance_module.get_chat_info = lambda chat_id: (0, 0, "Chat 1")
    finance_module.get_message_info = lambda *args, **kwargs: (
        {"message_text": "question"},
        {"message_text": "answer", "relevant_chunks": "context"},
    )
    finance_module.get_text_from_url = lambda url: "page text"
    finance_module.retrieve_message_from_db = lambda *args, **kwargs: []
    _register_module("api_endpoints.financeGPT.chatbot_endpoints", finance_module)

    reactive_agent_module = types.ModuleType("agents.reactive_agent")

    class FakeReactiveDocumentAgent:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def process_query_stream(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            return [{"answer": "streamed"}]

        def process_query_stream_guest(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            return [{"answer": "guest-streamed"}]

        def process_query(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"answer": "agent answer", "message_id": 1, "sources": []}

    reactive_agent_module.ReactiveDocumentAgent = FakeReactiveDocumentAgent
    reactive_agent_module.WorkflowReactiveAgent = FakeReactiveDocumentAgent
    _register_module("agents.reactive_agent", reactive_agent_module)

    agents_config_module = types.ModuleType("agents.config")

    class FakeAgentConfig:
        @staticmethod
        def is_agent_enabled() -> bool:
            return False

        @staticmethod
        def should_use_fallback() -> bool:
            return True

    agents_config_module.AgentConfig = FakeAgentConfig
    _register_module("agents.config", agents_config_module)

    google_flow_module = types.ModuleType("google_auth_oauthlib.flow")

    class FakeFlow:
        def __init__(self) -> None:
            self.redirect_uri = ""
            self.credentials = SimpleNamespace(_id_token="test-id-token")

        @classmethod
        def from_client_secrets_file(cls, *args: Any, **kwargs: Any) -> FakeFlow:
            return cls()

        def authorization_url(self, state: str) -> tuple[str, str]:
            return "http://example.com/oauth", state

        def fetch_token(self, authorization_response: str) -> None:
            return None

    google_flow_module.Flow = FakeFlow
    _register_module("google_auth_oauthlib.flow", google_flow_module)

    google_id_token_module = types.ModuleType("google.oauth2.id_token")
    google_id_token_module.verify_oauth2_token = lambda **kwargs: {
        "email": "oauth@example.com",
        "sub": "oauth-sub",
        "name": "OAuth User",
        "picture": "https://example.com/avatar.png",
    }
    _register_module("google.oauth2.id_token", google_id_token_module)

    google_requests_module = types.ModuleType("google.auth.transport.requests")

    class FakeRequest:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    google_requests_module.Request = FakeRequest
    _register_module("google.auth.transport.requests", google_requests_module)

    flask_mysql_connector_module = types.ModuleType("flask_mysql_connector")

    class FakeMySQL:
        def __init__(self, app: Any) -> None:
            self.connection = MagicMock()

    flask_mysql_connector_module.MySQL = FakeMySQL
    _register_module("flask_mysql_connector", flask_mysql_connector_module)

    stripe_module = types.ModuleType("stripe")

    class SignatureVerificationError(Exception):
        pass

    class FakeWebhook:
        @staticmethod
        def construct_event(data: bytes, signature: str | None, secret: str) -> dict[str, str]:
            return {"type": "test.event"}

    stripe_module.Webhook = FakeWebhook
    stripe_module.error = SimpleNamespace(SignatureVerificationError=SignatureVerificationError)
    stripe_module.api_key = ""
    _register_module("stripe", stripe_module)

    anthropic_module = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.completions = SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(completion="anthropic answer")
            )

    anthropic_module.Anthropic = FakeAnthropic
    anthropic_module.HUMAN_PROMPT = "Human:"
    anthropic_module.AI_PROMPT = "Assistant:"
    _register_module("anthropic", anthropic_module)

    openai_module = types.ModuleType("openai")

    class FakeOpenAIClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.embeddings = SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    data=[
                        SimpleNamespace(embedding=[0.1] * 768)
                        for _ in kwargs.get("input", [])
                    ]
                )
            )
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="openai answer"))]
                    )
                )
            )

    class NotFoundError(Exception):
        pass

    openai_module.OpenAI = FakeOpenAIClient
    openai_module.NotFoundError = NotFoundError
    _register_module("openai", openai_module)

    tika_module = types.ModuleType("tika")
    tika_module.parser = SimpleNamespace(from_buffer=lambda *args, **kwargs: {"content": "stub text"})
    _register_module("tika", tika_module)

    ray_module = types.ModuleType("ray")
    ray_module.is_initialized = lambda: True
    ray_module.init = lambda *args, **kwargs: None
    ray_module.get = lambda value: value

    def remote(fn: Any) -> Any:
        fn.remote = fn
        return fn

    ray_module.remote = remote
    _register_module("ray", ray_module)

    langchain_splitter_module = types.ModuleType("langchain.text_splitter")

    class FakeRecursiveCharacterTextSplitter:
        def __init__(
            self,
            *,
            chunk_size: int,
            chunk_overlap: int,
            separators: list[str],
            length_function: Any,
        ) -> None:
            self.chunk_size = chunk_size

        def split_text(self, text: str) -> list[str]:
            if not text:
                return []
            return [text[index : index + self.chunk_size] for index in range(0, len(text), self.chunk_size)]

    langchain_splitter_module.RecursiveCharacterTextSplitter = FakeRecursiveCharacterTextSplitter
    _register_module("langchain.text_splitter", langchain_splitter_module)


_install_import_stubs()


@pytest.fixture(scope="session")
def app_module() -> Any:
    if "app" in sys.modules:
        del sys.modules["app"]
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True, JWT_SECRET_KEY="test-secret")
    return module


@pytest.fixture()
def client(app_module: Any) -> Any:
    return app_module.app.test_client()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


@pytest.fixture()
def refresh_headers(app_module: Any) -> dict[str, str]:
    with app_module.app.app_context():
        token = app_module.create_refresh_token(identity="test@example.com")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
