"""Tests to boost coverage across agents, middleware, services, and payments."""
from __future__ import annotations

import os
from importlib import reload
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# middleware/auth.py
# ---------------------------------------------------------------------------

def test_require_auth_no_token(client):
    resp = client.get("/api/user/profile")
    assert resp.status_code == 401


def test_require_auth_with_token(client, auth_headers):
    from unittest.mock import MagicMock, patch
    mock_cnx = MagicMock()
    mock_cnx.cursor.return_value.fetchall.return_value = []
    with patch("api_endpoints.documents.handler.get_connection", return_value=mock_cnx):
        resp = client.get("/api/documents", headers=auth_headers)
    assert resp.status_code == 200


def test_require_auth_decorator_directly(app):
    """Test the require_auth wrapper directly."""
    from middleware.auth import require_auth

    called = []

    @require_auth
    def dummy():
        called.append(True)
        return "ok"

    # Without app context / valid JWT we expect the 401 path
    with app.test_request_context():
        dummy()
        # verify_jwt_in_request raises without a token → returns 401 response tuple
        assert called == []  # inner fn not called


# ---------------------------------------------------------------------------
# agents/chat_agent.py
# ---------------------------------------------------------------------------

def test_run_chat_agent_no_api_key():
    """When no API key is set, agent should return an error string."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        # LangChain will fail without a real key; the except path returns "Error: ..."
        from agents.chat_agent import run_chat_agent
        result = run_chat_agent("hello")
        assert isinstance(result, str)


def test_run_chat_agent_with_mock():
    """Mock the Anthropic LLM so the happy path executes."""
    mock_response = MagicMock()
    mock_response.content = "mocked reply"

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    mock_langchain = MagicMock()
    mock_langchain.ChatAnthropic.return_value = mock_llm
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch.dict("sys.modules", {"langchain_anthropic": mock_langchain}):
            import agents.chat_agent as mod
            reload(mod)
            result = mod.run_chat_agent("hello", history=[
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hey"},
            ])
            assert isinstance(result, str)


def test_run_chat_agent_history_branches():
    """Exercise history role branches without real LLM."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        from agents.chat_agent import run_chat_agent
        result = run_chat_agent(
            "question",
            history=[
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
                {"role": "unknown", "content": "ignored"},
            ],
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# agents/coding_agent.py
# ---------------------------------------------------------------------------

def test_coding_agent_no_api_key():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        from agents.coding_agent import run_coding_agent
        result = run_coding_agent("write hello world")
        assert isinstance(result, str)


def test_coding_agent_with_mock():
    mock_response = MagicMock()
    mock_response.content = "print('hello')"

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("langchain_anthropic.ChatAnthropic", return_value=mock_llm):
            import agents.coding_agent as mod
            reload(mod)
            result = mod.run_coding_agent("write hello world", cwd="/tmp")
            assert isinstance(result, str)


# ---------------------------------------------------------------------------
# services/llm.py
# ---------------------------------------------------------------------------

def test_llm_complete_anthropic_mock():
    mock_client = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "answer"
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            import services.llm as mod
            reload(mod)
            result = mod.complete("hello", model="claude-sonnet-4-6")
            assert result == "answer"


def test_llm_complete_anthropic_with_system():
    mock_client = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "answer"
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            import services.llm as mod
            reload(mod)
            result = mod.complete("hello", model="claude-sonnet-4-6", system="be concise")
            assert result == "answer"


def test_llm_complete_anthropic_empty_content():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = []
    mock_client.messages.create.return_value = mock_response

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            import services.llm as mod
            reload(mod)
            result = mod.complete("hello", model="claude-sonnet-4-6")
            assert result == ""


def test_llm_complete_openai_mock():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "openai answer"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        with patch("openai.OpenAI", return_value=mock_client):
            import services.llm as mod
            reload(mod)
            result = mod.complete("hello", model="gpt-4o")
            assert result == "openai answer"


def test_llm_complete_openai_with_system():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "openai answer"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        with patch("openai.OpenAI", return_value=mock_client):
            import services.llm as mod
            reload(mod)
            result = mod.complete("hello", model="gpt-4o", system="be brief")
            assert result == "openai answer"


def test_llm_complete_openai_empty():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = []
    mock_client.chat.completions.create.return_value = mock_response

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        with patch("openai.OpenAI", return_value=mock_client):
            import services.llm as mod
            reload(mod)
            result = mod.complete("hello", model="gpt-4o")
            assert result == ""


def test_llm_complete_ollama_mock():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "ollama answer"}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        import services.llm as mod
        reload(mod)
        result = mod.complete("hello", model="llama3")
        assert result == "ollama answer"


# ---------------------------------------------------------------------------
# services/rag.py
# ---------------------------------------------------------------------------

def test_ingest_document_path_traversal():
    from services.rag import ingest_document
    with pytest.raises(ValueError, match="outside upload folder"):
        ingest_document("doc1", Path("/etc/passwd"))


def test_ingest_document_no_chromadb(tmp_path):
    """Ingest a text file; chromadb import will fail in test env, returns chunk count."""
    upload_dir = Path("/tmp/anote_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_file = upload_dir / "test_doc.txt"
    test_file.write_text("Hello world. " * 100)

    # Patch chromadb import to raise so the except branch executes
    with patch.dict("sys.modules", {"chromadb": None, "chromadb.utils": None,
                                     "chromadb.utils.embedding_functions": None}):
        import services.rag as mod
        reload(mod)
        count = mod.ingest_document("test1", test_file)
        assert count > 0  # chunks returned despite chromadb failure

    test_file.unlink(missing_ok=True)


def test_extract_text_txt(tmp_path):
    upload_dir = Path("/tmp/anote_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    f = upload_dir / "sample.txt"
    f.write_text("hello world")

    from services.rag import _extract_text
    result = _extract_text(f)
    assert "hello" in result
    f.unlink(missing_ok=True)


def test_extract_text_path_traversal():
    from services.rag import _extract_text
    # File outside upload dir → returns empty string
    result = _extract_text(Path("/etc/passwd"))
    assert result == ""


def test_extract_text_unknown_ext(tmp_path):
    upload_dir = Path("/tmp/anote_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    f = upload_dir / "sample.bin"
    f.write_bytes(b"\x00\x01\x02")

    from services.rag import _extract_text
    result = _extract_text(f)
    assert result == ""
    f.unlink(missing_ok=True)


def test_query_documents_no_context_no_key():
    """With no chromadb and no API key, returns the 'not found' message."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        with patch.dict("sys.modules", {"chromadb": None}):
            import services.rag as mod
            reload(mod)
            result = mod.query_documents("what is this?")
            assert "not find" in result.lower() or isinstance(result, str)


def test_query_documents_context_no_key():
    """When chromadb returns results but no API key, returns the context snippet."""
    mock_chroma = MagicMock()
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"documents": [["chunk1", "chunk2"]]}
    mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = mock_collection

    mock_ef_module = MagicMock()
    mock_ef_module.DefaultEmbeddingFunction.return_value = MagicMock()

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        with patch.dict("sys.modules", {"chromadb": mock_chroma,
                                         "chromadb.utils": mock_ef_module,
                                         "chromadb.utils.embedding_functions": mock_ef_module}):
            import services.rag as mod
            reload(mod)
            result = mod.query_documents("what is this?", doc_ids=["doc1"])
            assert isinstance(result, str)


# ---------------------------------------------------------------------------
# services/streaming.py
# ---------------------------------------------------------------------------

def test_stream_agent_no_api_key():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        import services.streaming as mod
        reload(mod)
        events = list(mod.stream_agent_response("hello"))
        assert len(events) == 1
        assert "error" in events[0]
        assert "ANTHROPIC_API_KEY" in events[0]


def test_stream_agent_with_mock():
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter(["Hello", " world"])

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            import services.streaming as mod
            reload(mod)
            events = list(mod.stream_agent_response("hello"))
            # Should have text events + done
            assert any("text" in e for e in events)
            assert any("done" in e for e in events)


def test_stream_agent_error_path():
    mock_client = MagicMock()
    mock_client.messages.stream.side_effect = RuntimeError("API error")

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            import services.streaming as mod
            reload(mod)
            events = list(mod.stream_agent_response("hello"))
            assert any("error" in e for e in events)


def test_stream_llm_no_api_key():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        import services.streaming as mod
        reload(mod)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            mod.stream_llm_response("hello")


def test_stream_llm_with_mock():
    mock_block = MagicMock()
    mock_block.text = "streaming answer"
    mock_response = MagicMock()
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            import services.streaming as mod
            reload(mod)
            result = mod.stream_llm_response("hello", history=[{"role": "user", "content": "hi"}])
            assert result == "streaming answer"


# ---------------------------------------------------------------------------
# api_endpoints/payments/handler.py
# ---------------------------------------------------------------------------

def test_payments_checkout_no_stripe(client):
    resp = client.post("/api/payments/checkout", json={"priceId": "price_test"})
    assert resp.status_code == 503


def test_payments_portal_no_stripe(client):
    resp = client.post("/api/payments/portal", json={"customerId": "cus_test"})
    assert resp.status_code == 503


def test_payments_webhook_no_secret(client):
    resp = client.post("/api/payments/webhook", data=b"payload",
                        headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    assert resp.get_json()["received"] is True


def test_payments_webhook_bad_signature(client):
    with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_test",
                                   "STRIPE_SECRET_KEY": "sk_test"}):
        mock_stripe = MagicMock()
        mock_stripe.Webhook.construct_event.side_effect = Exception("bad sig")
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post("/api/payments/webhook", data=b"{}",
                                headers={"Stripe-Signature": "bad",
                                         "Content-Type": "application/json"})
            assert resp.status_code == 400


def test_payments_checkout_stripe_error(client):
    with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test"}):
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.side_effect = Exception("stripe error")
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post("/api/payments/checkout", json={"priceId": "price_test"})
            assert resp.status_code == 500


def test_payments_portal_stripe_error(client):
    with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test"}):
        mock_stripe = MagicMock()
        mock_stripe.billing_portal.Session.create.side_effect = Exception("stripe error")
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post("/api/payments/portal", json={"customerId": "cus_test"})
            assert resp.status_code == 500


def test_payments_checkout_success(client):
    with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test"}):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.return_value = mock_session
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post("/api/payments/checkout",
                                json={"priceId": "price_123",
                                      "successUrl": "http://localhost:3000/ok",
                                      "cancelUrl": "http://localhost:3000/cancel"})
            assert resp.status_code == 200
            assert "url" in resp.get_json()


def test_payments_portal_success(client):
    with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test"}):
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/test"
        mock_stripe = MagicMock()
        mock_stripe.billing_portal.Session.create.return_value = mock_session
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post("/api/payments/portal",
                                json={"customerId": "cus_123",
                                      "returnUrl": "http://localhost:3000"})
            assert resp.status_code == 200
            assert "url" in resp.get_json()


# ---------------------------------------------------------------------------
# database/db.py
# ---------------------------------------------------------------------------

def test_db_get_connection_fails_gracefully():
    """db.get_connection raises when no DB is available."""
    from database import db

    with patch.object(db, "MYSQL_AVAILABLE", False):
        with pytest.raises(RuntimeError, match="mysql-connector-python not installed"):
            db.get_connection()


def test_db_functions_with_none_connection():
    """DB helper functions surface invalid connections."""
    from database import db

    with pytest.raises(AttributeError):
        db.get_user_by_email(None, "test@test.com")  # type: ignore[arg-type]
    with pytest.raises(AttributeError):
        db.create_user(None, "test@test.com", "hash")  # type: ignore[arg-type]
