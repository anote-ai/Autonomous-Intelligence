"""Social media content planning and channel-constraint enforcement.

This module implements a scoped slice of the "autonomous social media
workflow" epic (see GitHub issue #142):

- Build a planned content queue ("content calendar") from a posting goal,
  a cadence, and a list of channels.
- Define per-channel formatting/scheduling constraints (character limits,
  allowed media types, posting windows, approval requirements).
- Define a brand voice profile with hard constraints (prohibited claims /
  topics) that every draft must be checked against before it is allowed
  to publish.
- Track the lifecycle of a planned post (draft -> scheduled -> published /
  blocked / failed) and produce actionable retry guidance when a post is
  blocked or fails to publish.

Out of scope for this slice (left for follow-up, see PR description):
source collection / drafting via an LLM, real channel API integrations,
engagement metric ingestion, and the operator console UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class Channel(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class PostStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class ChannelConstraints:
    """Channel-specific formatting and scheduling rules."""

    channel: Channel
    max_chars: int
    allowed_media_types: tuple[str, ...] = ()
    max_media_attachments: int = 0
    requires_approval: bool = False
    # Allowed posting windows expressed as (start_hour, end_hour) in UTC,
    # using a 24h clock. Empty tuple means "no restriction".
    posting_windows: tuple[tuple[int, int], ...] = ()


# Default constraints per supported channel. Callers may override by
# passing their own ChannelConstraints into the planner.
DEFAULT_CHANNEL_CONSTRAINTS: dict[Channel, ChannelConstraints] = {
    Channel.TWITTER: ChannelConstraints(
        channel=Channel.TWITTER,
        max_chars=280,
        allowed_media_types=("image", "gif", "video"),
        max_media_attachments=4,
        requires_approval=False,
        posting_windows=((0, 24),),
    ),
    Channel.LINKEDIN: ChannelConstraints(
        channel=Channel.LINKEDIN,
        max_chars=3000,
        allowed_media_types=("image", "video", "document"),
        max_media_attachments=9,
        requires_approval=True,
        posting_windows=((13, 18),),
    ),
    Channel.INSTAGRAM: ChannelConstraints(
        channel=Channel.INSTAGRAM,
        max_chars=2200,
        allowed_media_types=("image", "video"),
        max_media_attachments=10,
        requires_approval=True,
        posting_windows=((11, 22),),
    ),
    Channel.FACEBOOK: ChannelConstraints(
        channel=Channel.FACEBOOK,
        max_chars=63206,
        allowed_media_types=("image", "video", "link"),
        max_media_attachments=10,
        requires_approval=False,
        posting_windows=((0, 24),),
    ),
}


@dataclass(frozen=True)
class BrandVoiceProfile:
    """Hard constraints that every draft must satisfy before publish."""

    name: str
    prohibited_terms: tuple[str, ...] = ()
    prohibited_topics: tuple[str, ...] = ()
    required_disclaimers: tuple[str, ...] = ()

    def violations(self, text: str) -> list[str]:
        """Return a list of human-readable violation descriptions, if any."""
        lowered = text.lower()
        problems: list[str] = []
        for term in self.prohibited_terms:
            if term.lower() in lowered:
                problems.append(f"prohibited term detected: '{term}'")
        for topic in self.prohibited_topics:
            if topic.lower() in lowered:
                problems.append(f"prohibited topic detected: '{topic}'")
        for disclaimer in self.required_disclaimers:
            if disclaimer.lower() not in lowered:
                problems.append(f"missing required disclaimer: '{disclaimer}'")
        return problems


@dataclass
class PlannedPost:
    """A single planned item in the content calendar."""

    id: str
    channel: Channel
    text: str
    scheduled_for: datetime
    media_types: tuple[str, ...] = ()
    status: PostStatus = PostStatus.DRAFT
    blocked_reasons: list[str] = field(default_factory=list)
    retry_guidance: Optional[str] = None
    published_at: Optional[datetime] = None
    engagement: dict = field(default_factory=dict)


def _next_window_start(scheduled_for: datetime, windows: tuple[tuple[int, int], ...]) -> datetime:
    """Return the next datetime that falls within one of the given windows."""
    if not windows:
        return scheduled_for
    for start_hour, end_hour in sorted(windows):
        if start_hour <= scheduled_for.hour < end_hour:
            return scheduled_for
    # Move to the start of the next available window, today or tomorrow.
    candidates = []
    for start_hour, _ in windows:
        candidate = scheduled_for.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if candidate <= scheduled_for:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    return min(candidates)


def check_channel_constraints(
    text: str,
    channel: Channel,
    media_types: tuple[str, ...] = (),
    constraints: Optional[ChannelConstraints] = None,
) -> list[str]:
    """Validate a draft against channel-specific formatting rules.

    Returns a list of violation strings (empty list means the draft is
    compliant with formatting/media rules for the channel).
    """
    rules = constraints or DEFAULT_CHANNEL_CONSTRAINTS[channel]
    violations: list[str] = []

    if len(text) > rules.max_chars:
        violations.append(
            f"text exceeds {rules.channel.value} character limit "
            f"({len(text)} > {rules.max_chars})"
        )
    if not text.strip():
        violations.append("text is empty")

    if len(media_types) > rules.max_media_attachments:
        violations.append(
            f"too many media attachments for {rules.channel.value} "
            f"({len(media_types)} > {rules.max_media_attachments})"
        )
    for media_type in media_types:
        if rules.allowed_media_types and media_type not in rules.allowed_media_types:
            violations.append(
                f"media type '{media_type}' not supported on {rules.channel.value}"
            )

    return violations


def build_retry_guidance(reasons: list[str], channel: Channel) -> str:
    """Produce actionable, human-readable guidance for a blocked/failed post."""
    rules = DEFAULT_CHANNEL_CONSTRAINTS[channel]
    tips: list[str] = []
    for reason in reasons:
        if "character limit" in reason:
            tips.append(f"Shorten the text to {rules.max_chars} characters or fewer.")
        elif "media type" in reason:
            tips.append(
                f"Remove or swap unsupported media; {rules.channel.value} allows: "
                f"{', '.join(rules.allowed_media_types) or 'no media'}."
            )
        elif "too many media attachments" in reason:
            tips.append(f"Reduce attachments to {rules.max_media_attachments} or fewer.")
        elif "prohibited term" in reason or "prohibited topic" in reason:
            tips.append("Remove or rephrase the flagged term/topic and resubmit for review.")
        elif "missing required disclaimer" in reason:
            tips.append("Add the required disclaimer text before resubmitting.")
        elif "empty" in reason:
            tips.append("Add draft text before scheduling.")
        elif "awaiting required approval" in reason:
            tips.append("Get operator approval before this post can publish.")
        else:
            tips.append(f"Resolve: {reason}.")
    return " ".join(tips) if tips else "Resolve the reported issues and resubmit."


class ContentCalendarPlanner:
    """Builds and manages a queue of planned social posts."""

    def __init__(
        self,
        brand_voice: BrandVoiceProfile,
        channel_constraints: Optional[dict[Channel, ChannelConstraints]] = None,
    ):
        self.brand_voice = brand_voice
        self.channel_constraints = channel_constraints or DEFAULT_CHANNEL_CONSTRAINTS
        self._posts: dict[str, PlannedPost] = {}
        self._next_id = 1

    def _allocate_id(self) -> str:
        post_id = f"post-{self._next_id}"
        self._next_id += 1
        return post_id

    def plan_queue(
        self,
        drafts: list[dict],
        start: datetime,
        cadence: timedelta = timedelta(days=1),
    ) -> list[PlannedPost]:
        """Generate a planned queue of content from a list of draft dicts.

        Each draft dict must contain ``channel`` (str or Channel) and
        ``text``, and may contain ``media_types`` (iterable of str).
        Posts are scheduled at ``start``, ``start + cadence``,
        ``start + 2*cadence``, ... and then snapped forward to the next
        valid posting window for their channel.
        """
        planned: list[PlannedPost] = []
        for index, draft in enumerate(drafts):
            channel = Channel(draft["channel"])
            rules = self.channel_constraints[channel]
            raw_time = start + cadence * index
            scheduled_for = _next_window_start(raw_time, rules.posting_windows)

            post = PlannedPost(
                id=self._allocate_id(),
                channel=channel,
                text=draft["text"],
                scheduled_for=scheduled_for,
                media_types=tuple(draft.get("media_types", ())),
                status=(
                    PostStatus.PENDING_APPROVAL if rules.requires_approval else PostStatus.DRAFT
                ),
            )
            self._posts[post.id] = post
            planned.append(post)
        return planned

    def validate_post(self, post: PlannedPost) -> list[str]:
        """Run all enforcement checks (channel + brand voice) on a post."""
        rules = self.channel_constraints[post.channel]
        reasons = check_channel_constraints(
            post.text, post.channel, post.media_types, rules
        )
        reasons.extend(self.brand_voice.violations(post.text))
        return reasons

    def approve(self, post_id: str) -> PlannedPost:
        post = self._posts[post_id]
        if post.status != PostStatus.PENDING_APPROVAL:
            raise ValueError(f"post {post_id} is not pending approval (status={post.status})")
        post.status = PostStatus.SCHEDULED
        return post

    def attempt_publish(self, post_id: str, now: Optional[datetime] = None) -> PlannedPost:
        """Validate constraints and either publish, block, or mark failed.

        - If channel/brand-voice constraints are violated -> BLOCKED, with
          retry guidance attached.
        - If still pending approval -> BLOCKED (approval required).
        - If the scheduled time is in the future relative to ``now`` -> the
          post stays unpublished (no state change) since it's not due yet.
        - Otherwise -> PUBLISHED.
        """
        post = self._posts[post_id]
        now = now or datetime.utcnow()

        reasons = self.validate_post(post)
        if post.status == PostStatus.PENDING_APPROVAL:
            reasons = list(reasons) + ["awaiting required approval"]

        if reasons:
            post.status = PostStatus.BLOCKED
            post.blocked_reasons = reasons
            post.retry_guidance = build_retry_guidance(reasons, post.channel)
            return post

        if post.scheduled_for > now:
            # Not due yet; leave status untouched.
            return post

        post.status = PostStatus.PUBLISHED
        post.published_at = now
        post.blocked_reasons = []
        post.retry_guidance = None
        return post

    def mark_failed(self, post_id: str, error: str) -> PlannedPost:
        """Record a publish-time failure (e.g. channel API error) with retry guidance."""
        post = self._posts[post_id]
        post.status = PostStatus.FAILED
        post.blocked_reasons = [error]
        post.retry_guidance = (
            f"Publish attempt failed: {error}. Verify channel credentials/connectivity "
            "and retry; if the error persists, escalate to an operator."
        )
        return post

    def record_engagement(self, post_id: str, metrics: dict) -> PlannedPost:
        post = self._posts[post_id]
        if post.status != PostStatus.PUBLISHED:
            raise ValueError(f"cannot record engagement for unpublished post {post_id}")
        post.engagement.update(metrics)
        return post

    def get_post(self, post_id: str) -> PlannedPost:
        return self._posts[post_id]

    def queue(self) -> list[PlannedPost]:
        return sorted(self._posts.values(), key=lambda p: p.scheduled_for)

    def console_summary(self) -> dict:
        """Operator-console-friendly summary: counts by status + blocked/failed detail."""
        posts = self.queue()
        by_status: dict[str, int] = {}
        for post in posts:
            by_status[post.status.value] = by_status.get(post.status.value, 0) + 1
        actionable = [
            {
                "id": post.id,
                "channel": post.channel.value,
                "status": post.status.value,
                "reasons": post.blocked_reasons,
                "retry_guidance": post.retry_guidance,
            }
            for post in posts
            if post.status in (PostStatus.BLOCKED, PostStatus.FAILED)
        ]
        published = [
            {
                "id": post.id,
                "channel": post.channel.value,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "engagement": post.engagement,
            }
            for post in posts
            if post.status == PostStatus.PUBLISHED
        ]
        return {
            "counts_by_status": by_status,
            "actionable": actionable,
            "published": published,
        }
