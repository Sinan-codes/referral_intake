"""Tests for the duplicate matcher in `app.duplicates.matcher`.

The matching rule is (last name, date of birth) -- deliberately not full
name, so a nickname/spelling variant across sources still matches. These
tests cover: the match key itself (including the fields that make a
referral unmatchable), grouping across and within sources, the decoys the
rule is meant to reject (same name/different DOB, same DOB/different last
name), and that `apply_duplicate_groups` sets `duplicate_group_id` without
mutating the input.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.duplicates.matcher import (
    apply_duplicate_groups,
    duplicate_group_id,
    find_duplicate_groups,
    match_key,
)
from app.models.referral import PatientName, Referral, ReferralSource, Urgency


def _referral(
    *,
    id: str = "web_form:1",
    source: ReferralSource = ReferralSource.WEB_FORM,
    first_name: str | None = "Bob",
    last_name: str | None = "Barnhardt",
    date_of_birth: date | None = date(1962, 12, 31),
) -> Referral:
    raw_full_name = " ".join(part for part in (first_name, last_name) if part) or "Unknown"
    return Referral(
        id=id,
        source=source,
        source_record_id=id,
        received_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        patient_name=PatientName(
            raw_full_name=raw_full_name, first_name=first_name, last_name=last_name
        ),
        date_of_birth=date_of_birth,
        referring_provider=None,
        reason=None,
        urgency=Urgency.ROUTINE,
    )


# --- match_key -------------------------------------------------------------------


class TestMatchKey:
    def test_returns_lowercased_last_name_and_dob(self):
        referral = _referral(last_name="Barnhardt", date_of_birth=date(1962, 12, 31))

        assert match_key(referral) == ("barnhardt", date(1962, 12, 31))

    def test_strips_and_lowercases_last_name(self):
        referral = _referral(last_name="  BARNHARDT  ")

        assert match_key(referral) == ("barnhardt", date(1962, 12, 31))

    def test_none_when_last_name_missing(self):
        referral = _referral(last_name=None)

        assert match_key(referral) is None

    def test_none_when_last_name_blank(self):
        referral = _referral(last_name="   ")

        assert match_key(referral) is None

    def test_none_when_date_of_birth_missing(self):
        referral = _referral(date_of_birth=None)

        assert match_key(referral) is None


# --- duplicate_group_id ------------------------------------------------------------


class TestDuplicateGroupId:
    def test_is_deterministic_and_readable(self):
        key = ("barnhardt", date(1962, 12, 31))

        assert duplicate_group_id(key) == "dup:barnhardt:1962-12-31"

    def test_same_key_always_produces_same_id(self):
        key = ("ito", date(1998, 3, 22))

        assert duplicate_group_id(key) == duplicate_group_id(key)


# --- find_duplicate_groups ----------------------------------------------------------


class TestFindDuplicateGroups:
    def test_groups_matching_referrals_across_sources(self):
        a = _referral(id="web_form:1", source=ReferralSource.WEB_FORM, first_name="Bob")
        b = _referral(id="efax:1", source=ReferralSource.EFAX, first_name="Robert")

        groups = find_duplicate_groups([a, b])

        assert groups == {"dup:barnhardt:1962-12-31": [a, b]}

    def test_groups_matching_referrals_within_the_same_source(self):
        a = _referral(id="efax:1", source=ReferralSource.EFAX)
        b = _referral(id="efax:2", source=ReferralSource.EFAX)

        groups = find_duplicate_groups([a, b])

        assert groups == {"dup:barnhardt:1962-12-31": [a, b]}

    def test_ignores_first_name_so_nicknames_still_match(self):
        bob = _referral(id="web_form:1", first_name="Bob")
        robert = _referral(id="web_form:2", first_name="Robert")

        groups = find_duplicate_groups([bob, robert])

        assert list(groups.values()) == [[bob, robert]]

    def test_same_name_but_different_dob_is_not_a_duplicate(self):
        a = _referral(id="a", date_of_birth=date(1962, 12, 31))
        b = _referral(id="b", date_of_birth=date(1990, 5, 1))

        assert find_duplicate_groups([a, b]) == {}

    def test_same_dob_but_different_last_name_is_not_a_duplicate(self):
        a = _referral(id="a", last_name="Barnhardt", date_of_birth=date(1962, 12, 31))
        b = _referral(id="b", last_name="Ito", date_of_birth=date(1962, 12, 31))

        assert find_duplicate_groups([a, b]) == {}

    def test_singleton_is_not_a_duplicate_group(self):
        a = _referral(id="a")

        assert find_duplicate_groups([a]) == {}

    def test_referral_missing_last_name_or_dob_is_never_grouped(self):
        no_last_name = _referral(id="a", last_name=None)
        no_dob = _referral(id="b", date_of_birth=None)
        matches_neither = _referral(id="c")

        groups = find_duplicate_groups([no_last_name, no_dob, matches_neither])

        assert groups == {}

    def test_groups_larger_than_two(self):
        a = _referral(id="a", source=ReferralSource.WEB_FORM)
        b = _referral(id="b", source=ReferralSource.EFAX)
        c = _referral(id="c", source=ReferralSource.EHR_FHIR)

        groups = find_duplicate_groups([a, b, c])

        assert groups == {"dup:barnhardt:1962-12-31": [a, b, c]}

    def test_multiple_independent_groups(self):
        barnhardt_a = _referral(id="a", last_name="Barnhardt")
        barnhardt_b = _referral(id="b", last_name="Barnhardt")
        ito_a = _referral(id="c", last_name="Ito", date_of_birth=date(1998, 3, 22))
        ito_b = _referral(id="d", last_name="Ito", date_of_birth=date(1998, 3, 22))
        unmatched = _referral(id="e", last_name="Quigley", date_of_birth=date(1953, 1, 13))

        groups = find_duplicate_groups([barnhardt_a, barnhardt_b, ito_a, ito_b, unmatched])

        assert set(groups.keys()) == {"dup:barnhardt:1962-12-31", "dup:ito:1998-03-22"}
        assert groups["dup:barnhardt:1962-12-31"] == [barnhardt_a, barnhardt_b]
        assert groups["dup:ito:1998-03-22"] == [ito_a, ito_b]


# --- apply_duplicate_groups ---------------------------------------------------------


class TestApplyDuplicateGroups:
    def test_sets_duplicate_group_id_on_matched_referrals(self):
        a = _referral(id="a")
        b = _referral(id="b")

        result = apply_duplicate_groups([a, b])

        assert result[0].duplicate_group_id == "dup:barnhardt:1962-12-31"
        assert result[1].duplicate_group_id == result[0].duplicate_group_id

    def test_matched_referrals_report_possible_duplicate(self):
        a = _referral(id="a")
        b = _referral(id="b")

        result = apply_duplicate_groups([a, b])

        assert result[0].possible_duplicate is True
        assert result[1].possible_duplicate is True

    def test_unmatched_referral_keeps_duplicate_group_id_none(self):
        unmatched = _referral(id="a", last_name="Quigley", date_of_birth=date(1953, 1, 13))

        result = apply_duplicate_groups([unmatched])

        assert result[0].duplicate_group_id is None
        assert result[0].possible_duplicate is False

    def test_preserves_input_order(self):
        a = _referral(id="a", last_name="Quigley", date_of_birth=date(1953, 1, 13))
        b = _referral(id="b")
        c = _referral(id="c")

        result = apply_duplicate_groups([a, b, c])

        assert [r.id for r in result] == ["a", "b", "c"]

    def test_does_not_mutate_the_input_referrals(self):
        a = _referral(id="a")
        b = _referral(id="b")
        referrals = [a, b]

        apply_duplicate_groups(referrals)

        assert a.duplicate_group_id is None
        assert b.duplicate_group_id is None

    def test_empty_input_returns_empty_list(self):
        assert apply_duplicate_groups([]) == []
