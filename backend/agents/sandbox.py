"""Runtime sandbox controls for dynamically registered (and select built-in) tools.

This module implements the "Runtime Isolation" and "Policy Integration" pieces of
issue #133 ("Harden the runtime sandbox for built-in and generated tools"):

- Execution timeouts: every dynamic tool call runs in a worker thread with a hard
  wall-clock deadline. A tool that loops indefinitely is terminated (the worker
  thread is abandoned and the call fails closed) instead of hanging the request.
- Per-session/per-workspace execution quotas: each session has a bounded number of
  dynamic-tool calls and a bounded number of concurrently in-flight calls.
- Network egress restrictions: dynamically registered tools get a restricted
  `requests`-like client that only allows hosts on an allowlist (configurable,
  defaults to deny-all in production-like enforcement mode).
- Policy/enforcement modes: `SandboxPolicy` supports a stricter "production" mode
  and a looser "development" mode, selected via the `SANDBOX_ENFORCEMENT_MODE`
  env var, mirroring the dev/prod split called for in the issue.
- Auditable violations: every blocked/timed-out/quota-exceeded call raises a
  `SandboxViolation` with a machine-readable `reason` code and is recorded via
  `record_violation` for observability, without leaking raw tool source or
  request bodies.

This is intentionally scoped to the *dynamic tool* execution path
(`_tool_run_dynamic` / `register_tool` in `autonomous_agent.py`), which is the
highest-risk surface called out in the issue (LLM-authored code executed via
`exec`). CPU/memory rlimits, filesystem syscall interception, and full container
isolation are out of scope for this change (see PR description).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------

class SandboxViolation(Exception):
    """Raised when a tool execution is blocked or terminated by the sandbox.

    `reason` is a short, stable, machine-readable code suitable for metrics/audit
    logs (never includes raw tool source, request bodies, or other sensitive
    runtime details).
    """

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(message)


_VIOLATION_LOG: list[dict] = []
_VIOLATION_LOG_LOCK = threading.Lock()
_MAX_VIOLATION_LOG = 500


def record_violation(
    *, reason: str, tool_name: str, session_id: str, detail: str = ""
) -> None:
    """Record a sandbox violation for observability/audit purposes.

    Deliberately stores only metadata (reason code, tool name, session id, short
    detail) — never the offending source code, arguments, or response bodies.
    """
    entry = {
        "ts": time.time(),
        "reason": reason,
        "tool_name": tool_name,
        "session_id": session_id,
        "detail": detail[:200],
    }
    logger.warning(
        "Sandbox violation: reason=%s tool=%s session=%s detail=%s",
        reason, tool_name, session_id, entry["detail"],
    )
    with _VIOLATION_LOG_LOCK:
        _VIOLATION_LOG.append(entry)
        if len(_VIOLATION_LOG) > _MAX_VIOLATION_LOG:
            del _VIOLATION_LOG[: len(_VIOLATION_LOG) - _MAX_VIOLATION_LOG]


def get_recent_violations(limit: int = 50) -> list[dict]:
    """Return the most recent sandbox violations (for an observability endpoint)."""
    with _VIOLATION_LOG_LOCK:
        return list(_VIOLATION_LOG[-limit:])


def clear_violations() -> None:
    """Test helper — clear the in-memory violation log."""
    with _VIOLATION_LOG_LOCK:
        _VIOLATION_LOG.clear()


# ---------------------------------------------------------------------------
# Policy — dev vs production enforcement modes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SandboxPolicy:
    """Runtime enforcement policy for dynamic tool execution.

    `mode` selects a named preset (development/production); individual fields can
    still be overridden via env vars for fine-grained control.
    """

    mode: str
    timeout_seconds: float
    max_calls_per_session: int
    max_concurrent_per_session: int
    network_allowlist: frozenset
    allow_network: bool

    @classmethod
    def from_env(cls) -> SandboxPolicy:
        mode = os.getenv("SANDBOX_ENFORCEMENT_MODE", "production").strip().lower()
        if mode not in ("development", "production"):
            mode = "production"

        if mode == "development":
            default_timeout = 15.0
            default_max_calls = 200
            default_max_concurrent = 8
            default_allow_network = True
        else:
            default_timeout = 5.0
            default_max_calls = 50
            default_max_concurrent = 3
            default_allow_network = False

        timeout_seconds = float(
            os.getenv("SANDBOX_TOOL_TIMEOUT_SECONDS", str(default_timeout))
        )
        max_calls_per_session = int(
            os.getenv("SANDBOX_MAX_CALLS_PER_SESSION", str(default_max_calls))
        )
        max_concurrent_per_session = int(
            os.getenv("SANDBOX_MAX_CONCURRENT_PER_SESSION", str(default_max_concurrent))
        )
        allow_network = (
            os.getenv(
                "SANDBOX_ALLOW_NETWORK", "true" if default_allow_network else "false"
            )
            .strip()
            .lower()
            == "true"
        )
        raw_allowlist = os.getenv("SANDBOX_NETWORK_ALLOWLIST", "")
        network_allowlist = frozenset(
            host.strip().lower() for host in raw_allowlist.split(",") if host.strip()
        )

        return cls(
            mode=mode,
            timeout_seconds=timeout_seconds,
            max_calls_per_session=max_calls_per_session,
            max_concurrent_per_session=max_concurrent_per_session,
            network_allowlist=network_allowlist,
            allow_network=allow_network,
        )


_DEFAULT_POLICY: SandboxPolicy | None = None


def get_policy() -> SandboxPolicy:
    """Return the process-wide sandbox policy, loading it from env on first use."""
    global _DEFAULT_POLICY
    if _DEFAULT_POLICY is None:
        _DEFAULT_POLICY = SandboxPolicy.from_env()
    return _DEFAULT_POLICY


def reset_policy_cache() -> None:
    """Test helper — force the next get_policy() call to re-read env vars."""
    global _DEFAULT_POLICY
    _DEFAULT_POLICY = None


def is_host_allowed(url: str, policy: SandboxPolicy | None = None) -> bool:
    """Check whether a URL's host is permitted under the current network policy."""
    policy = policy or get_policy()
    if not policy.allow_network:
        return False
    if not policy.network_allowlist:
        # Network is enabled but no explicit allowlist configured — deny by
        # default (fail closed) rather than silently allowing every host.
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    return host in policy.network_allowlist


# ---------------------------------------------------------------------------
# Per-session execution quotas
# ---------------------------------------------------------------------------

@dataclass
class _SessionQuotaState:
    total_calls: int = 0
    in_flight: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class SessionQuotaTracker:
    """Tracks dynamic-tool call counts/concurrency per session (or workspace)."""

    def __init__(self) -> None:
        self._sessions: dict = {}
        self._global_lock = threading.Lock()

    def _state(self, session_id: str) -> _SessionQuotaState:
        with self._global_lock:
            state = self._sessions.get(session_id)
            if state is None:
                state = _SessionQuotaState()
                self._sessions[session_id] = state
            return state

    def acquire(self, session_id: str, policy: SandboxPolicy) -> None:
        """Reserve quota for one call. Raises SandboxViolation if exhausted."""
        state = self._state(session_id)
        with state.lock:
            if state.total_calls >= policy.max_calls_per_session:
                raise SandboxViolation(
                    "quota_exceeded",
                    f"Session has exceeded its dynamic tool call quota "
                    f"({policy.max_calls_per_session} calls).",
                )
            if state.in_flight >= policy.max_concurrent_per_session:
                raise SandboxViolation(
                    "concurrency_exceeded",
                    f"Session has exceeded its concurrent dynamic tool call limit "
                    f"({policy.max_concurrent_per_session}).",
                )
            state.total_calls += 1
            state.in_flight += 1

    def release(self, session_id: str) -> None:
        state = self._state(session_id)
        with state.lock:
            state.in_flight = max(0, state.in_flight - 1)

    def reset(self, session_id: str) -> None:
        with self._global_lock:
            self._sessions.pop(session_id, None)


_QUOTA_TRACKER = SessionQuotaTracker()


def get_quota_tracker() -> SessionQuotaTracker:
    return _QUOTA_TRACKER


# ---------------------------------------------------------------------------
# Timeout-enforced execution
# ---------------------------------------------------------------------------

def run_with_limits(
    fn: Callable[[], Any],
    *,
    tool_name: str,
    session_id: str,
    policy: SandboxPolicy | None = None,
) -> Any:
    """Run `fn` under sandbox runtime limits (timeout + per-session quota).

    `fn` runs in a dedicated daemon thread so that a runaway/infinite-looping
    tool cannot block process shutdown — the calling thread waits at most
    `policy.timeout_seconds` and then treats the call as terminated, regardless
    of whether the underlying Python thread (which cannot be forcibly killed)
    has actually returned. This bounds the *caller's* wait time even though,
    like most in-process Python sandboxes, it cannot reclaim CPU from a thread
    that ignores cooperative cancellation (see PR description for the
    process-isolation follow-up this implies).

    Raises SandboxViolation (fail closed) on timeout or quota exhaustion. Any
    exception raised by `fn` itself propagates unchanged.
    """
    policy = policy or get_policy()

    try:
        get_quota_tracker().acquire(session_id, policy)
    except SandboxViolation as exc:
        record_violation(
            reason=exc.reason, tool_name=tool_name, session_id=session_id,
            detail=str(exc),
        )
        raise

    result_box: dict = {}

    def _target() -> None:
        try:
            result_box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller's thread
            result_box["error"] = exc

    worker = threading.Thread(
        target=_target, name=f"tool-sandbox-{tool_name}", daemon=True
    )
    worker.start()
    worker.join(timeout=policy.timeout_seconds)

    try:
        if worker.is_alive():
            record_violation(
                reason="timeout",
                tool_name=tool_name,
                session_id=session_id,
                detail=f"exceeded {policy.timeout_seconds}s limit",
            )
            raise SandboxViolation(
                "timeout",
                f"Tool '{tool_name}' exceeded its {policy.timeout_seconds}s "
                f"execution time limit and was terminated.",
            )
        if "error" in result_box:
            raise result_box["error"]
        return result_box.get("value")
    finally:
        get_quota_tracker().release(session_id)


# ---------------------------------------------------------------------------
# Restricted network client for dynamic tools
# ---------------------------------------------------------------------------

class RestrictedRequests:
    """Drop-in stand-in for the `requests` module exposed to dynamic tool code.

    Delegates to the real `requests` library but enforces the sandbox's network
    egress policy (allowlist) on every call. Tools that need network access in
    development mode work normally against allowlisted hosts; in production mode
    (or with no allowlist configured) all network calls fail closed.
    """

    def __init__(self, session_id: str, policy: SandboxPolicy | None = None):
        self._session_id = session_id
        self._policy = policy or get_policy()

    def _check(self, url: str, method: str) -> None:
        if not is_host_allowed(url, self._policy):
            record_violation(
                reason="network_blocked",
                tool_name="<dynamic_tool>",
                session_id=self._session_id,
                detail=f"{method} {urlparse(url).hostname or url}",
            )
            raise SandboxViolation(
                "network_blocked",
                f"Network access to '{urlparse(url).hostname or url}' is not "
                f"permitted by the current sandbox policy.",
            )

    def get(self, url: str, *args: Any, **kwargs: Any) -> Any:
        import requests as _requests

        self._check(url, "GET")
        return _requests.get(url, *args, **kwargs)

    def post(self, url: str, *args: Any, **kwargs: Any) -> Any:
        import requests as _requests

        self._check(url, "POST")
        return _requests.post(url, *args, **kwargs)

    def put(self, url: str, *args: Any, **kwargs: Any) -> Any:
        import requests as _requests

        self._check(url, "PUT")
        return _requests.put(url, *args, **kwargs)

    def delete(self, url: str, *args: Any, **kwargs: Any) -> Any:
        import requests as _requests

        self._check(url, "DELETE")
        return _requests.delete(url, *args, **kwargs)
