"""Tests for backend/features.py feature-flag helpers."""

import importlib
import os
from unittest.mock import patch

import pytest


def _reload_features():
    """Re-import the features module so env vars picked up at import time are fresh."""
    import features  # noqa: PLC0415
    importlib.reload(features)
    return features


class TestIsFinanceGptEnabled:
    def test_default_is_true(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_FINANCE_GPT", None)
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is True

    def test_explicit_true(self):
        with patch.dict(os.environ, {"ENABLE_FINANCE_GPT": "true"}):
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is True

    def test_explicit_false_lowercase(self):
        with patch.dict(os.environ, {"ENABLE_FINANCE_GPT": "false"}):
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is False

    def test_explicit_false_uppercase(self):
        with patch.dict(os.environ, {"ENABLE_FINANCE_GPT": "FALSE"}):
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is False

    def test_zero_disables(self):
        with patch.dict(os.environ, {"ENABLE_FINANCE_GPT": "0"}):
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is False

    def test_off_disables(self):
        with patch.dict(os.environ, {"ENABLE_FINANCE_GPT": "off"}):
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is False

    def test_one_enables(self):
        with patch.dict(os.environ, {"ENABLE_FINANCE_GPT": "1"}):
            f = _reload_features()
            assert f.is_finance_gpt_enabled() is True


class TestIsAgentEnabled:
    def test_default_is_true(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_AGENTS", None)
            f = _reload_features()
            assert f.is_agent_enabled() is True

    def test_explicit_false(self):
        with patch.dict(os.environ, {"ENABLE_AGENTS": "false"}):
            f = _reload_features()
            assert f.is_agent_enabled() is False

    def test_explicit_true(self):
        with patch.dict(os.environ, {"ENABLE_AGENTS": "true"}):
            f = _reload_features()
            assert f.is_agent_enabled() is True

    def test_no_disables(self):
        with patch.dict(os.environ, {"ENABLE_AGENTS": "no"}):
            f = _reload_features()
            assert f.is_agent_enabled() is False
