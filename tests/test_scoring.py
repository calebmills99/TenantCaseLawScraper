"""Tests for relevance scoring and opinion-selection helpers in scraper.py.

Covers:
- score_relevance
- CourtListenerSource._select_lead_opinion_id
"""

import pytest

from scraper import CourtListenerSource, score_relevance


# ---------------------------------------------------------------------------
# score_relevance
# ---------------------------------------------------------------------------


class TestScoreRelevance:
    # --- Topic weights ---

    def test_strong_topic_weight(self):
        """Each strong topic contributes 0.22 (minus stub penalty if text < 500 chars)."""
        long_text = "x" * 600
        score = score_relevance(long_text, "", ["unpermitted_unit"])
        assert abs(score - 0.22) < 1e-9

    def test_strong_topic_unpermitted_unit(self):
        long_text = "x" * 600
        assert abs(score_relevance(long_text, "", ["unpermitted_unit"]) - 0.22) < 1e-9

    def test_strong_topic_rent_disgorgement(self):
        long_text = "x" * 600
        assert abs(score_relevance(long_text, "", ["rent_disgorgement"]) - 0.22) < 1e-9

    def test_strong_topic_rso_coverage(self):
        long_text = "x" * 600
        assert abs(score_relevance(long_text, "", ["rso_coverage"]) - 0.22) < 1e-9

    def test_strong_topic_certificate_of_occupancy(self):
        long_text = "x" * 600
        assert abs(score_relevance(long_text, "", ["certificate_of_occupancy"]) - 0.22) < 1e-9

    def test_medium_topic_weight(self):
        long_text = "x" * 600
        score = score_relevance(long_text, "", ["landlord_harassment"])
        assert abs(score - 0.11) < 1e-9

    def test_medium_topic_wrongful_eviction(self):
        long_text = "x" * 600
        assert abs(score_relevance(long_text, "", ["wrongful_eviction"]) - 0.11) < 1e-9

    def test_medium_topic_habitability(self):
        long_text = "x" * 600
        assert abs(score_relevance(long_text, "", ["habitability"]) - 0.11) < 1e-9

    def test_weak_topic_weight(self):
        long_text = "x" * 600
        score = score_relevance(long_text, "", ["some_unknown_topic"])
        assert abs(score - 0.04) < 1e-9

    # --- Combination bonuses ---

    def test_carter_cohen_combo_bonus(self):
        """unpermitted_unit + rent_disgorgement adds 0.18 bonus."""
        long_text = "x" * 600
        topics = ["unpermitted_unit", "rent_disgorgement"]
        # Expected: 0.22 + 0.22 + 0.18 = 0.62
        expected = 0.22 + 0.22 + 0.18
        assert abs(score_relevance(long_text, "", topics) - expected) < 1e-9

    def test_salazar_combo_bonus(self):
        """rso_coverage + unpermitted_unit adds 0.12 bonus."""
        long_text = "x" * 600
        topics = ["rso_coverage", "unpermitted_unit"]
        # Expected: 0.22 + 0.22 + 0.12 = 0.56
        expected = 0.22 + 0.22 + 0.12
        assert abs(score_relevance(long_text, "", topics) - expected) < 1e-9

    def test_both_combos_fire_independently(self):
        """Both Carter and Salazar combos can fire at the same time."""
        long_text = "x" * 600
        topics = ["unpermitted_unit", "rent_disgorgement", "rso_coverage"]
        # 3×0.22 + 0.18 (Carter) + 0.12 (Salazar) = 0.66 + 0.30 = 0.96
        expected = 3 * 0.22 + 0.18 + 0.12
        assert abs(score_relevance(long_text, "", topics) - expected) < 1e-9

    def test_carter_combo_requires_both_topics(self):
        """Only one topic from Carter combo → no bonus."""
        long_text = "x" * 600
        score_only_unpermitted = score_relevance(long_text, "", ["unpermitted_unit"])
        score_only_disgorgement = score_relevance(long_text, "", ["rent_disgorgement"])
        score_combo = score_relevance(
            long_text, "", ["unpermitted_unit", "rent_disgorgement"]
        )
        assert score_combo > score_only_unpermitted + score_only_disgorgement - 1e-9

    def test_salazar_combo_requires_both_topics(self):
        """Only one topic from Salazar combo → no bonus."""
        long_text = "x" * 600
        score_only_rso = score_relevance(long_text, "", ["rso_coverage"])
        score_only_unpermitted = score_relevance(long_text, "", ["unpermitted_unit"])
        score_combo = score_relevance(long_text, "", ["rso_coverage", "unpermitted_unit"])
        assert score_combo > score_only_rso + score_only_unpermitted - 1e-9

    # --- Stub penalty ---

    def test_stub_penalty_halves_score(self):
        """Text under 500 chars → score halved."""
        short_text = "x" * 499
        long_text = "x" * 600
        topics = ["unpermitted_unit"]
        short_score = score_relevance(short_text, "", topics)
        long_score = score_relevance(long_text, "", topics)
        assert abs(short_score - long_score / 2) < 1e-9

    def test_stub_threshold_is_500_chars(self):
        """Exactly 500 chars should NOT trigger stub penalty."""
        text_500 = "x" * 500
        text_499 = "x" * 499
        topics = ["unpermitted_unit"]
        assert score_relevance(text_500, "", topics) > score_relevance(text_499, "", topics)

    def test_no_stub_penalty_at_exactly_500_chars(self):
        text_500 = "x" * 500
        long_text = "x" * 600
        topics = ["rso_coverage"]
        assert abs(score_relevance(text_500, "", topics) - score_relevance(long_text, "", topics)) < 1e-9

    # --- Score clamp ---

    def test_score_clamped_to_one(self):
        """Scores above 1.0 must be clamped to 1.0."""
        long_text = "x" * 600
        # All four strong topics + both combos → 4×0.22 + 0.18 + 0.12 = 1.18 → 1.0
        topics = [
            "unpermitted_unit",
            "rent_disgorgement",
            "rso_coverage",
            "certificate_of_occupancy",
        ]
        assert score_relevance(long_text, "", topics) == 1.0

    def test_score_clamped_to_zero(self):
        """Score can never go below 0.0."""
        assert score_relevance("", "", []) >= 0.0

    def test_all_four_strong_plus_both_combos_reach_max(self):
        """A case hitting all four strong topics + both combos should score 1.0."""
        long_text = "x" * 600
        topics = [
            "unpermitted_unit",
            "rent_disgorgement",
            "rso_coverage",
            "certificate_of_occupancy",
        ]
        assert score_relevance(long_text, "", topics) == 1.0

    def test_zero_topics_zero_score(self):
        """No topics and no phrase match → score 0.0."""
        long_text = "x" * 600
        assert score_relevance(long_text, "", []) == 0.0

    def test_unrelated_case_scores_zero(self):
        """A random unrelated case (no topics, no phrase match) should score 0.0."""
        text = "The weather in San Francisco was pleasant this morning."
        assert score_relevance(text, "weather", []) == 0.0

    def test_returns_float(self):
        assert isinstance(score_relevance("text", "", []), float)

    def test_score_in_range(self):
        long_text = "x" * 600
        topics = ["unpermitted_unit", "rent_disgorgement"]
        s = score_relevance(long_text, "", topics)
        assert 0.0 <= s <= 1.0


# ---------------------------------------------------------------------------
# CourtListenerSource._select_lead_opinion_id
# ---------------------------------------------------------------------------


def _make_opinion(op_id: str, op_type: str) -> dict:
    return {"id": op_id, "type": op_type}


class TestSelectLeadOpinionId:
    # --- Empty input ---

    def test_empty_list_returns_none(self):
        assert CourtListenerSource._select_lead_opinion_id([]) is None

    # --- Priority order ---

    def test_020lead_selected_first(self):
        opinions = [
            _make_opinion("lead-1", "020lead"),
            _make_opinion("unanimous-1", "015unanimous"),
            _make_opinion("combined-1", "010combined"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-1"

    def test_015unanimous_selected_when_no_lead(self):
        opinions = [
            _make_opinion("unanimous-1", "015unanimous"),
            _make_opinion("combined-1", "010combined"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "unanimous-1"

    def test_010combined_selected_when_no_lead_or_unanimous(self):
        opinions = [
            _make_opinion("combined-1", "010combined"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "combined-1"

    # --- Skipping concurrences and dissents ---

    def test_concurrence_skipped(self):
        """030concurrence should not be selected as lead."""
        opinions = [
            _make_opinion("concur-1", "030concurrence"),
            _make_opinion("lead-1", "020lead"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-1"

    def test_concurrenceinpart_skipped(self):
        """035concurrenceinpart should not be selected as lead."""
        opinions = [
            _make_opinion("concurinpart-1", "035concurrenceinpart"),
            _make_opinion("lead-1", "020lead"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-1"

    def test_dissent_skipped(self):
        """040dissent should not be selected as lead."""
        opinions = [
            _make_opinion("dissent-1", "040dissent"),
            _make_opinion("lead-1", "020lead"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-1"

    def test_all_skip_types_skipped_when_priority_available(self):
        opinions = [
            _make_opinion("dissent-1", "040dissent"),
            _make_opinion("concur-1", "030concurrence"),
            _make_opinion("concurinpart-1", "035concurrenceinpart"),
            _make_opinion("lead-1", "020lead"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-1"

    # --- Fallback to first non-skipped opinion ---

    def test_fallback_to_first_non_skipped(self):
        """When no priority type present, pick first non-skipped opinion."""
        opinions = [
            _make_opinion("dissent-1", "040dissent"),
            _make_opinion("other-1", "050other"),
            _make_opinion("lead-1", "020lead"),
        ]
        # 020lead is in priority → should be returned
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-1"

    def test_fallback_no_priority_types_present(self):
        """When no priority type and no skip types, first opinion is returned."""
        opinions = [
            _make_opinion("other-1", "050other"),
            _make_opinion("other-2", "060something"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "other-1"

    def test_fallback_skips_dissent_returns_next(self):
        """Fallback skips dissents and returns first non-skipped."""
        opinions = [
            _make_opinion("dissent-1", "040dissent"),
            _make_opinion("dissent-2", "040dissent"),
            _make_opinion("other-1", "050other"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "other-1"

    def test_fallback_skips_concurrence_returns_next(self):
        opinions = [
            _make_opinion("concur-1", "030concurrence"),
            _make_opinion("other-1", "050other"),
        ]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "other-1"

    # --- Last resort: all opinions are dissents/concurrences ---

    def test_last_resort_all_dissents_returns_first(self):
        """If every opinion is a dissent/concurrence, return opinions[0] (never None)."""
        opinions = [
            _make_opinion("dissent-1", "040dissent"),
            _make_opinion("concur-1", "030concurrence"),
            _make_opinion("concurinpart-1", "035concurrenceinpart"),
        ]
        result = CourtListenerSource._select_lead_opinion_id(opinions)
        assert result == "dissent-1"
        assert result is not None

    def test_never_returns_none_for_nonempty_input(self):
        """For any non-empty list, the result must not be None."""
        test_cases = [
            [_make_opinion("a", "040dissent")],
            [_make_opinion("b", "030concurrence")],
            [_make_opinion("c", "035concurrenceinpart")],
            [_make_opinion("d", "020lead")],
            [_make_opinion("e", "015unanimous")],
            [
                _make_opinion("f", "040dissent"),
                _make_opinion("g", "030concurrence"),
            ],
        ]
        for opinions in test_cases:
            result = CourtListenerSource._select_lead_opinion_id(opinions)
            assert result is not None, f"Got None for opinions: {opinions}"

    def test_single_lead_opinion(self):
        opinions = [_make_opinion("lead-only", "020lead")]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "lead-only"

    def test_single_unanimous_opinion(self):
        opinions = [_make_opinion("unani-only", "015unanimous")]
        assert CourtListenerSource._select_lead_opinion_id(opinions) == "unani-only"
