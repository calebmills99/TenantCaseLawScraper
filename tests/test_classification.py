"""Tests for pure classification helpers in scraper.py.

Covers:
- _extract_query_terms
- query_matches
- classify_topics
- detect_outcome
"""

import pytest

from scraper import (
    ACRONYM_WHITELIST,
    QUERY_STOPWORDS,
    _extract_query_terms,
    classify_topics,
    detect_outcome,
    query_matches,
)


# ---------------------------------------------------------------------------
# _extract_query_terms
# ---------------------------------------------------------------------------


class TestExtractQueryTerms:
    def test_strips_common_stopwords(self):
        """Words from QUERY_STOPWORDS must not appear in the result."""
        result = _extract_query_terms("the court of california")
        assert result == []

    def test_strips_individual_stopwords(self):
        for word in ["the", "a", "and", "or", "of", "in", "on", "at"]:
            assert word not in _extract_query_terms(word)

    def test_preserves_acronym_rso(self):
        result = _extract_query_terms("rso coverage")
        assert "rso" in result

    def test_preserves_acronym_taho(self):
        result = _extract_query_terms("taho violation")
        assert "taho" in result

    def test_preserves_acronym_feha(self):
        result = _extract_query_terms("feha discrimination")
        assert "feha" in result

    def test_preserves_acronym_ada(self):
        result = _extract_query_terms("ada accommodation")
        assert "ada" in result

    def test_preserves_acronym_omi(self):
        result = _extract_query_terms("omi eviction")
        assert "omi" in result

    def test_preserves_acronym_ud(self):
        result = _extract_query_terms("ud filing")
        assert "ud" in result

    def test_preserves_acronym_ab(self):
        result = _extract_query_terms("ab 1482")
        assert "ab" in result

    def test_preserves_acronym_sb(self):
        result = _extract_query_terms("sb 567")
        assert "sb" in result

    def test_drops_short_tokens_not_in_whitelist(self):
        # "hi" is 2 chars, not in ACRONYM_WHITELIST → should be dropped
        result = _extract_query_terms("hi there some context")
        assert "hi" not in result

    def test_keeps_long_meaningful_tokens(self):
        result = _extract_query_terms("unpermitted unit")
        assert "unpermitted" in result

    def test_all_stopwords_returns_empty_list(self):
        assert _extract_query_terms("the court of california") == []

    def test_empty_string_returns_empty_list(self):
        assert _extract_query_terms("") == []

    def test_mixed_case_normalised(self):
        result = _extract_query_terms("RSO COVERAGE UNPERMITTED")
        assert "rso" in result
        assert "coverage" in result
        assert "unpermitted" in result

    def test_acronym_preserved_when_mixed_case(self):
        result = _extract_query_terms("RSO violation")
        assert "rso" in result

    def test_entire_acronym_whitelist_preserved(self):
        for acronym in ACRONYM_WHITELIST:
            result = _extract_query_terms(acronym)
            assert acronym in result, f"Acronym '{acronym}' should be preserved"

    def test_no_stopwords_in_result(self):
        query = "unpermitted unit RSO rent disgorgement"
        result = _extract_query_terms(query)
        for word in result:
            assert word not in QUERY_STOPWORDS or word in ACRONYM_WHITELIST

    def test_punctuation_split(self):
        result = _extract_query_terms("unpermitted, unit; RSO.")
        assert "unpermitted" in result
        assert "rso" in result

    def test_returns_list(self):
        assert isinstance(_extract_query_terms("rso coverage"), list)


# ---------------------------------------------------------------------------
# query_matches
# ---------------------------------------------------------------------------


class TestQueryMatches:
    def test_all_terms_present_returns_true(self):
        text = "This case involves an unpermitted unit subject to RSO."
        assert query_matches(text, "unpermitted unit RSO") is True

    def test_missing_one_term_returns_false(self):
        text = "This case involves an unpermitted unit only."
        # "rso" is not in the text
        assert query_matches(text, "unpermitted unit RSO") is False

    def test_case_insensitive_match(self):
        text = "UNPERMITTED UNIT RSO COVERAGE"
        assert query_matches(text, "unpermitted unit rso") is True

    def test_empty_query_returns_true(self):
        """Empty query → browse mode → always True."""
        assert query_matches("any text here", "") is True

    def test_all_stopword_query_returns_true(self):
        """All-stopword query extracts no terms → browse mode → True."""
        assert query_matches("any text here", "the court of california") is True

    # Regression test — the Justia filter bug
    def test_regression_unpermitted_unit_rso_must_not_match_only_unit(self):
        """query 'unpermitted unit RSO' must NOT match text containing only 'unit'.

        This is the Justia filter bug that matched on ANY term rather than ALL.
        """
        text = "unit"
        assert query_matches(text, "unpermitted unit RSO") is False

    def test_and_semantics_not_or(self):
        """All terms must be present, not just one."""
        text = "rent disgorgement case"
        # "unpermitted" is not in text
        assert query_matches(text, "unpermitted rent disgorgement") is False

    def test_single_term_present(self):
        assert query_matches("the unpermitted dwelling was inspected", "unpermitted") is True

    def test_single_term_absent(self):
        assert query_matches("regular rental agreement", "unpermitted") is False

    def test_acronym_term_match(self):
        assert query_matches("covered by the RSO ordinance", "rso") is True

    def test_empty_text_with_nonempty_query_returns_false(self):
        assert query_matches("", "unpermitted unit") is False


# ---------------------------------------------------------------------------
# classify_topics
# ---------------------------------------------------------------------------


class TestClassifyTopics:
    def test_empty_text_returns_empty_list(self):
        assert classify_topics("") == []

    def test_unpermitted_unit_detected(self):
        text = "The landlord rented an unpermitted unit without any permits."
        topics = classify_topics(text)
        assert "unpermitted_unit" in topics

    def test_rent_disgorgement_detected(self):
        text = "The court ordered rent disgorgement for the illegal tenancy."
        topics = classify_topics(text)
        assert "rent_disgorgement" in topics

    def test_rso_coverage_detected_by_acronym(self):
        text = "The unit is covered by the RSO and cannot be decontrolled."
        topics = classify_topics(text)
        assert "rso_coverage" in topics

    def test_rso_coverage_detected_by_full_name(self):
        text = "The Rent Stabilization Ordinance applies to this building."
        topics = classify_topics(text)
        assert "rso_coverage" in topics

    def test_certificate_of_occupancy_detected(self):
        text = "No certificate of occupancy was ever issued for the space."
        topics = classify_topics(text)
        assert "certificate_of_occupancy" in topics

    def test_landlord_harassment_detected(self):
        text = "The tenant alleged landlord harassment and intimidation."
        topics = classify_topics(text)
        assert "landlord_harassment" in topics

    def test_wrongful_eviction_detected(self):
        text = "Plaintiff claims wrongful eviction in violation of local law."
        topics = classify_topics(text)
        assert "wrongful_eviction" in topics

    def test_habitability_detected(self):
        text = "Defendant breached the implied warranty of habitability."
        topics = classify_topics(text)
        assert "habitability" in topics

    def test_multiple_topics_detected(self):
        text = (
            "This unpermitted unit is covered by the RSO. "
            "The landlord sought rent disgorgement and the court examined the "
            "certificate of occupancy."
        )
        topics = classify_topics(text)
        assert "unpermitted_unit" in topics
        assert "rso_coverage" in topics
        assert "rent_disgorgement" in topics
        assert "certificate_of_occupancy" in topics

    def test_unrelated_text_returns_no_topics(self):
        text = "The weather in San Francisco was pleasant this morning."
        topics = classify_topics(text)
        # Should not classify any tenant-rights topics
        assert topics == []

    def test_returns_list(self):
        assert isinstance(classify_topics("rso coverage"), list)

    def test_case_insensitive_classification(self):
        text = "UNPERMITTED UNIT covered by RENT STABILIZATION ORDINANCE"
        topics = classify_topics(text)
        assert "unpermitted_unit" in topics
        assert "rso_coverage" in topics


# ---------------------------------------------------------------------------
# detect_outcome
# ---------------------------------------------------------------------------


class TestDetectOutcome:
    def test_tenant_won_judgment_for_plaintiff(self):
        text = "The court entered judgment in favor of the plaintiff."
        assert detect_outcome(text) == "tenant_won"

    def test_tenant_won_summary_judgment_denied(self):
        text = "Defendant's motion for summary judgment denied."
        assert detect_outcome(text) == "tenant_won"

    def test_tenant_won_injunction_granted(self):
        text = "The injunction was granted preventing the eviction."
        assert detect_outcome(text) == "tenant_won"

    def test_landlord_won_judgment_for_defendant(self):
        text = "The court entered judgment in favor of the defendant."
        assert detect_outcome(text) == "landlord_won"

    def test_landlord_won_unlawful_detainer_granted(self):
        text = "The unlawful detainer was granted and a writ issued."
        assert detect_outcome(text) == "landlord_won"

    def test_landlord_won_summary_judgment_granted(self):
        text = "Summary judgment granted in favor of the defendant landlord."
        assert detect_outcome(text) == "landlord_won"

    def test_dismissed_with_prejudice(self):
        text = "The case was dismissed with prejudice."
        assert detect_outcome(text) == "dismissed"

    def test_dismissed_without_prejudice(self):
        text = "Plaintiff's complaint dismissed without prejudice."
        assert detect_outcome(text) == "dismissed"

    def test_settled(self):
        text = "The parties reached a settlement agreement and the case was settled."
        assert detect_outcome(text) == "settled"

    def test_stipulation_maps_to_settled(self):
        text = "Parties entered into a stipulation resolving the dispute."
        assert detect_outcome(text) == "settled"

    def test_unknown_for_unrelated_text(self):
        text = "The weather in San Francisco was pleasant this morning."
        assert detect_outcome(text) == "unknown"

    def test_unknown_for_empty_text(self):
        assert detect_outcome("") == "unknown"

    def test_returns_string(self):
        assert isinstance(detect_outcome("judgment for plaintiff"), str)
