from __future__ import annotations

from types import SimpleNamespace

from src.bot.bot.plugins.flirting import (
    FLIRT_RESPONSES,
    _match_flirt_category,
    _update_flirt_stats,
)


def test_flirt_response_buckets_have_enough_lines() -> None:
    assert len(FLIRT_RESPONSES["charming"]) >= 10
    assert len(FLIRT_RESPONSES["intellectual"]) >= 10


def test_match_flirt_category_picks_the_expected_bucket() -> None:
    assert _match_flirt_category("You are beautiful and gorgeous") == "charming"
    assert _match_flirt_category("That was a smart and intelligent idea") == "intellectual"
    assert _match_flirt_category("plain text with no trigger") is None


def test_update_flirt_stats_tracks_success_rate_and_streaks() -> None:
    stats = SimpleNamespace(
        total_attempts=0,
        successful_flirts=0,
        failed_flirts=0,
        favorite_category="charming",
        highest_skill_used="beginner",
        points_earned=0,
        success_rate=0.0,
        current_streak=0,
        best_streak=0,
        last_flirt_time=0,
        flirt_level="novice",
    )

    _update_flirt_stats(
        stats,
        success=True,
        category="charming",
        skill_level="beginner",
        points_earned=5,
    )
    _update_flirt_stats(
        stats,
        success=True,
        category="charming",
        skill_level="intermediate",
        points_earned=7,
    )
    _update_flirt_stats(
        stats,
        success=False,
        category="intellectual",
        skill_level="intermediate",
        points_earned=0,
    )

    assert stats.total_attempts == 3
    assert stats.successful_flirts == 2
    assert stats.failed_flirts == 1
    assert stats.current_streak == 0
    assert stats.best_streak == 2
    assert stats.points_earned == 12
    assert stats.success_rate == 66.66666666666666