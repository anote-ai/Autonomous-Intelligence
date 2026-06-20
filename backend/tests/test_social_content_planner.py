from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from services.social_content_planner import (
    BrandVoiceProfile,
    Channel,
    ChannelConstraints,
    ContentCalendarPlanner,
    PostStatus,
    build_retry_guidance,
    check_channel_constraints,
)


@pytest.fixture
def brand_voice() -> BrandVoiceProfile:
    return BrandVoiceProfile(
        name="Anote",
        prohibited_terms=("guaranteed returns",),
        prohibited_topics=("medical advice",),
        required_disclaimers=(),
    )


@pytest.fixture
def planner(brand_voice: BrandVoiceProfile) -> ContentCalendarPlanner:
    return ContentCalendarPlanner(brand_voice=brand_voice)


# ---------------------------------------------------------------------------
# Channel constraint enforcement
# ---------------------------------------------------------------------------


def test_check_channel_constraints_passes_for_compliant_tweet():
    violations = check_channel_constraints("Hello world", Channel.TWITTER, ("image",))
    assert violations == []


def test_check_channel_constraints_flags_over_length_text():
    violations = check_channel_constraints("x" * 281, Channel.TWITTER)
    assert any("character limit" in v for v in violations)


def test_check_channel_constraints_flags_empty_text():
    violations = check_channel_constraints("   ", Channel.TWITTER)
    assert any("empty" in v for v in violations)


def test_check_channel_constraints_flags_disallowed_media_type():
    violations = check_channel_constraints("Hi", Channel.TWITTER, ("document",))
    assert any("not supported" in v for v in violations)


def test_check_channel_constraints_flags_too_many_attachments():
    violations = check_channel_constraints(
        "Hi", Channel.TWITTER, ("image", "image", "image", "image", "image")
    )
    assert any("too many media attachments" in v for v in violations)


def test_custom_constraints_override_defaults():
    custom = ChannelConstraints(channel=Channel.TWITTER, max_chars=5)
    violations = check_channel_constraints("toolong", Channel.TWITTER, constraints=custom)
    assert any("character limit" in v for v in violations)


# ---------------------------------------------------------------------------
# Brand voice enforcement
# ---------------------------------------------------------------------------


def test_brand_voice_flags_prohibited_term(brand_voice: BrandVoiceProfile):
    violations = brand_voice.violations("We offer guaranteed returns on investment.")
    assert any("prohibited term" in v for v in violations)


def test_brand_voice_flags_prohibited_topic(brand_voice: BrandVoiceProfile):
    violations = brand_voice.violations("Here is some medical advice for you.")
    assert any("prohibited topic" in v for v in violations)


def test_brand_voice_requires_disclaimer():
    voice = BrandVoiceProfile(name="Anote", required_disclaimers=("not financial advice",))
    violations = voice.violations("Some neutral text.")
    assert any("missing required disclaimer" in v for v in violations)
    assert voice.violations("Some text. Not Financial Advice.") == []


def test_brand_voice_clean_text_has_no_violations(brand_voice: BrandVoiceProfile):
    assert brand_voice.violations("A perfectly fine post about our product.") == []


# ---------------------------------------------------------------------------
# Retry guidance
# ---------------------------------------------------------------------------


def test_build_retry_guidance_for_length_violation():
    guidance = build_retry_guidance(["text exceeds twitter character limit (300 > 280)"], Channel.TWITTER)
    assert "Shorten the text to 280" in guidance


def test_build_retry_guidance_for_prohibited_term():
    guidance = build_retry_guidance(["prohibited term detected: 'guaranteed returns'"], Channel.TWITTER)
    assert "Remove or rephrase" in guidance


def test_build_retry_guidance_falls_back_for_unknown_reason():
    guidance = build_retry_guidance(["some unexpected reason"], Channel.TWITTER)
    assert "Resolve: some unexpected reason." in guidance


# ---------------------------------------------------------------------------
# ContentCalendarPlanner: planning queue
# ---------------------------------------------------------------------------


def test_plan_queue_creates_posts_with_cadence(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)  # within twitter's all-day window
    drafts = [
        {"channel": "twitter", "text": "Post one"},
        {"channel": "twitter", "text": "Post two"},
    ]
    posts = planner.plan_queue(drafts, start=start, cadence=timedelta(days=1))
    assert len(posts) == 2
    assert posts[0].scheduled_for == start
    assert posts[1].scheduled_for == start + timedelta(days=1)
    assert all(p.status == PostStatus.DRAFT for p in posts)


def test_plan_queue_marks_approval_required_channels_pending(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 14, 0, 0)  # within linkedin's window
    drafts = [{"channel": "linkedin", "text": "Professional update"}]
    posts = planner.plan_queue(drafts, start=start)
    assert posts[0].status == PostStatus.PENDING_APPROVAL


def test_plan_queue_snaps_to_next_posting_window(planner: ContentCalendarPlanner):
    # LinkedIn's window is 13-18 UTC; scheduling at 02:00 should snap to 13:00 same day.
    start = datetime(2026, 6, 22, 2, 0, 0)
    drafts = [{"channel": "linkedin", "text": "Morning post"}]
    posts = planner.plan_queue(drafts, start=start)
    assert posts[0].scheduled_for == datetime(2026, 6, 22, 13, 0, 0)


def test_plan_queue_snaps_to_next_day_if_window_already_passed(planner: ContentCalendarPlanner):
    # LinkedIn's window is 13-18 UTC; scheduling at 20:00 should snap to 13:00 next day.
    start = datetime(2026, 6, 22, 20, 0, 0)
    drafts = [{"channel": "linkedin", "text": "Evening post"}]
    posts = planner.plan_queue(drafts, start=start)
    assert posts[0].scheduled_for == datetime(2026, 6, 23, 13, 0, 0)


# ---------------------------------------------------------------------------
# ContentCalendarPlanner: publish lifecycle
# ---------------------------------------------------------------------------


def test_attempt_publish_succeeds_for_compliant_due_post(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "Hello!"}], start=start)
    result = planner.attempt_publish(posts[0].id, now=start + timedelta(minutes=1))
    assert result.status == PostStatus.PUBLISHED
    assert result.published_at is not None
    assert result.blocked_reasons == []


def test_attempt_publish_not_due_yet_leaves_status_unchanged(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "Hello!"}], start=start)
    result = planner.attempt_publish(posts[0].id, now=start - timedelta(hours=1))
    assert result.status == PostStatus.DRAFT


def test_attempt_publish_blocks_on_channel_violation(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "x" * 300}], start=start)
    result = planner.attempt_publish(posts[0].id, now=start)
    assert result.status == PostStatus.BLOCKED
    assert result.retry_guidance is not None
    assert any("character limit" in r for r in result.blocked_reasons)


def test_attempt_publish_blocks_on_brand_voice_violation(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue(
        [{"channel": "twitter", "text": "We offer guaranteed returns!"}], start=start
    )
    result = planner.attempt_publish(posts[0].id, now=start)
    assert result.status == PostStatus.BLOCKED
    assert any("prohibited term" in r for r in result.blocked_reasons)


def test_attempt_publish_blocks_pending_approval_post(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 14, 0, 0)
    posts = planner.plan_queue([{"channel": "linkedin", "text": "Update"}], start=start)
    assert posts[0].status == PostStatus.PENDING_APPROVAL
    result = planner.attempt_publish(posts[0].id, now=start)
    assert result.status == PostStatus.BLOCKED
    assert any("awaiting required approval" in r for r in result.blocked_reasons)


def test_approve_then_publish_succeeds(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 14, 0, 0)
    posts = planner.plan_queue([{"channel": "linkedin", "text": "Update"}], start=start)
    planner.approve(posts[0].id)
    result = planner.attempt_publish(posts[0].id, now=start)
    assert result.status == PostStatus.PUBLISHED


def test_approve_raises_if_not_pending(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "Hello"}], start=start)
    with pytest.raises(ValueError):
        planner.approve(posts[0].id)


def test_mark_failed_records_retry_guidance(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "Hello"}], start=start)
    result = planner.mark_failed(posts[0].id, "channel API timeout")
    assert result.status == PostStatus.FAILED
    assert "channel API timeout" in result.blocked_reasons
    assert "Verify channel credentials" in result.retry_guidance


def test_record_engagement_requires_published_post(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "Hello"}], start=start)
    with pytest.raises(ValueError):
        planner.record_engagement(posts[0].id, {"likes": 10})


def test_record_engagement_on_published_post(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue([{"channel": "twitter", "text": "Hello"}], start=start)
    planner.attempt_publish(posts[0].id, now=start)
    result = planner.record_engagement(posts[0].id, {"likes": 10, "shares": 2})
    assert result.engagement == {"likes": 10, "shares": 2}


# ---------------------------------------------------------------------------
# Operator console summary
# ---------------------------------------------------------------------------


def test_console_summary_groups_by_status_and_surfaces_actionable_items(
    planner: ContentCalendarPlanner,
):
    start = datetime(2026, 6, 22, 1, 0, 0)
    posts = planner.plan_queue(
        [
            {"channel": "twitter", "text": "Good post"},
            {"channel": "twitter", "text": "x" * 300},
        ],
        start=start,
    )
    planner.attempt_publish(posts[0].id, now=start)
    planner.attempt_publish(posts[1].id, now=start)

    summary = planner.console_summary()
    assert summary["counts_by_status"]["published"] == 1
    assert summary["counts_by_status"]["blocked"] == 1
    assert len(summary["actionable"]) == 1
    assert summary["actionable"][0]["retry_guidance"]
    assert len(summary["published"]) == 1


def test_queue_returns_posts_sorted_by_scheduled_time(planner: ContentCalendarPlanner):
    start = datetime(2026, 6, 22, 1, 0, 0)
    drafts = [
        {"channel": "twitter", "text": "First"},
        {"channel": "twitter", "text": "Second"},
        {"channel": "twitter", "text": "Third"},
    ]
    planner.plan_queue(drafts, start=start, cadence=timedelta(hours=2))
    queued = planner.queue()
    assert [p.text for p in queued] == ["First", "Second", "Third"]
    assert queued[0].scheduled_for < queued[1].scheduled_for < queued[2].scheduled_for
