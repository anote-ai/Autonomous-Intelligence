"""Tests for backend/agents/sandbox.py — runtime isolation controls for
dynamically registered (and select built-in) tool execution.

Covers representative violation cases (timeout, quota exhaustion, concurrency
limit, network egress block) and representative safe/allowed cases, per the
acceptance criteria of issue #133.
"""
from __future__ import annotations

import time

import pytest
from agents import sandbox


@pytest.fixture(autouse=True)
def _reset_sandbox_state():
    """Each test gets a fresh policy cache, quota tracker, and violation log."""
    sandbox.reset_policy_cache()
    sandbox.clear_violations()
    yield
    sandbox.reset_policy_cache()
    sandbox.clear_violations()


def _policy(**overrides):
    base = dict(
        mode="production",
        timeout_seconds=0.2,
        max_calls_per_session=3,
        max_concurrent_per_session=2,
        network_allowlist=frozenset(),
        allow_network=False,
    )
    base.update(overrides)
    return sandbox.SandboxPolicy(**base)


# ---------------------------------------------------------------------------
# Policy construction from env
# ---------------------------------------------------------------------------

class TestPolicyFromEnv:
    def test_production_is_default_mode(self, monkeypatch):
        monkeypatch.delenv("SANDBOX_ENFORCEMENT_MODE", raising=False)
        policy = sandbox.SandboxPolicy.from_env()
        assert policy.mode == "production"
        assert policy.allow_network is False

    def test_development_mode_relaxes_limits(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENFORCEMENT_MODE", "development")
        policy = sandbox.SandboxPolicy.from_env()
        assert policy.mode == "development"
        assert policy.timeout_seconds > _policy().timeout_seconds or policy.timeout_seconds == 15.0
        assert policy.max_calls_per_session > 3

    def test_unknown_mode_falls_back_to_production(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENFORCEMENT_MODE", "yolo")
        policy = sandbox.SandboxPolicy.from_env()
        assert policy.mode == "production"

    def test_explicit_overrides_win(self, monkeypatch):
        monkeypatch.setenv("SANDBOX_ENFORCEMENT_MODE", "production")
        monkeypatch.setenv("SANDBOX_TOOL_TIMEOUT_SECONDS", "1.5")
        monkeypatch.setenv("SANDBOX_MAX_CALLS_PER_SESSION", "7")
        policy = sandbox.SandboxPolicy.from_env()
        assert policy.timeout_seconds == 1.5
        assert policy.max_calls_per_session == 7


# ---------------------------------------------------------------------------
# Execution timeout — "generated tool loops indefinitely" scenario
# ---------------------------------------------------------------------------

class TestRunWithLimitsTimeout:
    def test_safe_fast_call_succeeds(self):
        policy = _policy()
        result = sandbox.run_with_limits(
            lambda: 6 * 7, tool_name="fast_tool", session_id="s1", policy=policy
        )
        assert result == 42

    def test_runaway_call_is_terminated_and_recorded(self):
        policy = _policy(timeout_seconds=0.1)

        def infinite_loop():
            while True:
                time.sleep(0.01)

        with pytest.raises(sandbox.SandboxViolation) as exc_info:
            sandbox.run_with_limits(
                infinite_loop, tool_name="runaway_tool", session_id="s1", policy=policy
            )
        assert exc_info.value.reason == "timeout"

        violations = sandbox.get_recent_violations()
        assert any(
            v["reason"] == "timeout" and v["tool_name"] == "runaway_tool"
            for v in violations
        )

    def test_tool_exception_propagates_unchanged(self):
        policy = _policy()

        def boom():
            raise ValueError("dynamic tool bug")

        with pytest.raises(ValueError, match="dynamic tool bug"):
            sandbox.run_with_limits(boom, tool_name="buggy_tool", session_id="s1", policy=policy)

    def test_quota_released_after_timeout(self):
        """A timed-out call must still release its concurrency slot."""
        policy = _policy(timeout_seconds=0.1, max_concurrent_per_session=1)

        def infinite_loop():
            while True:
                time.sleep(0.01)

        with pytest.raises(sandbox.SandboxViolation):
            sandbox.run_with_limits(
                infinite_loop, tool_name="runaway", session_id="s-release", policy=policy
            )

        # Slot should be free again for a subsequent fast call.
        result = sandbox.run_with_limits(
            lambda: "ok", tool_name="fast", session_id="s-release", policy=policy
        )
        assert result == "ok"


# ---------------------------------------------------------------------------
# Per-session execution quotas
# ---------------------------------------------------------------------------

class TestSessionQuotas:
    def test_quota_exhaustion_blocks_further_calls(self):
        policy = _policy(max_calls_per_session=2, max_concurrent_per_session=5)
        session_id = "quota-session"

        sandbox.run_with_limits(lambda: 1, tool_name="t", session_id=session_id, policy=policy)
        sandbox.run_with_limits(lambda: 2, tool_name="t", session_id=session_id, policy=policy)

        with pytest.raises(sandbox.SandboxViolation) as exc_info:
            sandbox.run_with_limits(lambda: 3, tool_name="t", session_id=session_id, policy=policy)
        assert exc_info.value.reason == "quota_exceeded"

    def test_quota_is_isolated_per_session(self):
        policy = _policy(max_calls_per_session=1, max_concurrent_per_session=5)

        sandbox.run_with_limits(lambda: 1, tool_name="t", session_id="session-a", policy=policy)
        # A different session should not be affected by session-a's quota.
        result = sandbox.run_with_limits(
            lambda: 2, tool_name="t", session_id="session-b", policy=policy
        )
        assert result == 2

    def test_concurrency_limit_blocks_overlapping_calls(self):
        tracker = sandbox.SessionQuotaTracker()
        policy = _policy(max_calls_per_session=10, max_concurrent_per_session=1)

        tracker.acquire("c1", policy)
        with pytest.raises(sandbox.SandboxViolation) as exc_info:
            tracker.acquire("c1", policy)
        assert exc_info.value.reason == "concurrency_exceeded"

        tracker.release("c1")
        # Now a slot should be free again.
        tracker.acquire("c1", policy)


# ---------------------------------------------------------------------------
# Network egress restrictions
# ---------------------------------------------------------------------------

class TestNetworkPolicy:
    def test_network_blocked_when_disabled(self):
        policy = _policy(allow_network=False)
        assert sandbox.is_host_allowed("https://api.example.com/data", policy) is False

    def test_network_blocked_with_no_allowlist_even_if_enabled(self):
        policy = _policy(allow_network=True, network_allowlist=frozenset())
        assert sandbox.is_host_allowed("https://api.example.com/data", policy) is False

    def test_allowlisted_host_is_permitted(self):
        policy = _policy(
            allow_network=True, network_allowlist=frozenset({"api.example.com"})
        )
        assert sandbox.is_host_allowed("https://api.example.com/data", policy) is True

    def test_non_allowlisted_host_is_blocked(self):
        policy = _policy(
            allow_network=True, network_allowlist=frozenset({"api.example.com"})
        )
        assert sandbox.is_host_allowed("https://evil.example.org/exfil", policy) is False

    def test_restricted_requests_blocks_disallowed_host(self):
        policy = _policy(allow_network=False)
        client = sandbox.RestrictedRequests("session-net", policy=policy)
        with pytest.raises(sandbox.SandboxViolation) as exc_info:
            client.get("https://evil.example.org/exfil")
        assert exc_info.value.reason == "network_blocked"
        violations = sandbox.get_recent_violations()
        assert any(v["reason"] == "network_blocked" for v in violations)

    def test_restricted_requests_allows_allowlisted_host(self, monkeypatch):
        policy = _policy(allow_network=True, network_allowlist=frozenset({"api.example.com"}))
        client = sandbox.RestrictedRequests("session-net-ok", policy=policy)

        calls = {}

        def fake_get(url, *args, **kwargs):
            calls["url"] = url
            return "fake-response"

        monkeypatch.setattr("requests.get", fake_get)
        result = client.get("https://api.example.com/data")
        assert result == "fake-response"
        assert calls["url"] == "https://api.example.com/data"


# ---------------------------------------------------------------------------
# Violation observability
# ---------------------------------------------------------------------------

class TestViolationLog:
    def test_record_violation_does_not_leak_raw_detail_beyond_200_chars(self):
        sandbox.record_violation(
            reason="timeout",
            tool_name="t",
            session_id="s",
            detail="x" * 1000,
        )
        entry = sandbox.get_recent_violations()[-1]
        assert len(entry["detail"]) == 200

    def test_clear_violations_empties_log(self):
        sandbox.record_violation(reason="timeout", tool_name="t", session_id="s")
        assert sandbox.get_recent_violations()
        sandbox.clear_violations()
        assert sandbox.get_recent_violations() == []
