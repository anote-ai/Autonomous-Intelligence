"""Smoke tests for Slack bot helpers — no Slack/Anthropic credentials needed."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
import os


def test_extract_query_strips_mention():
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-fake")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "fake")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake")
    import importlib, sys
    for mod in list(sys.modules):
        if "slack_bot" in mod or (mod.startswith("app") and "bots" in str(sys.modules[mod])):
            del sys.modules[mod]
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    with patch("slack_bolt.App"):
        with patch("anthropic.Anthropic"):
            import app as bot
    result = bot.extract_query("<@U12345> explain this code")
    assert result == "explain this code"


def test_extract_query_empty_returns_none():
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-fake")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "fake")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake")
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    with patch("slack_bolt.App"):
        with patch("anthropic.Anthropic"):
            import app as bot
    result = bot.extract_query("<@U12345>   ")
    assert result is None


def test_trim_response_short():
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-fake")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "fake")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake")
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    with patch("slack_bolt.App"):
        with patch("anthropic.Anthropic"):
            import app as bot
    assert bot.trim_response("short") == "short"


def test_trim_response_long():
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-fake")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "fake")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake")
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    with patch("slack_bolt.App"):
        with patch("anthropic.Anthropic"):
            import app as bot
    long_text = "x" * 3000
    result = bot.trim_response(long_text)
    assert len(result) < 3000
    assert "truncated" in result
