"""Tests for the status workflow in `app.models.referral`.

The assignment's diagram:

    new -> in_review -> {accepted -> scheduled, rejected}

`scheduled` and `rejected` are terminal, and any transition not on this
diagram must be rejected. The workflow is small enough to enumerate
completely rather than sample a few cases -- a bug here (e.g. an
accidentally-permissive edit to ALLOWED_TRANSITIONS) is exactly the kind
the assignment calls out as high-stakes, so these pin the full allowed and
disallowed set instead of just the happy path.
"""

from __future__ import annotations

import pytest

from app.models.referral import ALLOWED_TRANSITIONS, ReferralStatus, is_valid_transition

ALL_STATUSES = list(ReferralStatus)

EXPECTED_ALLOWED: set[tuple[ReferralStatus, ReferralStatus]] = {
    (ReferralStatus.NEW, ReferralStatus.IN_REVIEW),
    (ReferralStatus.IN_REVIEW, ReferralStatus.ACCEPTED),
    (ReferralStatus.IN_REVIEW, ReferralStatus.REJECTED),
    (ReferralStatus.ACCEPTED, ReferralStatus.SCHEDULED),
}

ALL_PAIRS = [(current, target) for current in ALL_STATUSES for target in ALL_STATUSES]
DISALLOWED_PAIRS = [pair for pair in ALL_PAIRS if pair not in EXPECTED_ALLOWED]


def _sort_key(pair: tuple[ReferralStatus, ReferralStatus]) -> tuple[str, str]:
    return (pair[0].value, pair[1].value)


class TestAllowedTransitions:
    @pytest.mark.parametrize("current,target", sorted(EXPECTED_ALLOWED, key=_sort_key))
    def test_allowed_transition_is_valid(self, current, target):
        assert is_valid_transition(current, target) is True

    @pytest.mark.parametrize("current,target", sorted(DISALLOWED_PAIRS, key=_sort_key))
    def test_disallowed_transition_is_invalid(self, current, target):
        assert is_valid_transition(current, target) is False

    def test_matches_the_assignment_diagram_exactly(self):
        actual = {
            (status, target) for status, targets in ALLOWED_TRANSITIONS.items() for target in targets
        }

        assert actual == EXPECTED_ALLOWED

    def test_no_status_can_transition_to_itself(self):
        for status in ALL_STATUSES:
            assert is_valid_transition(status, status) is False


class TestTerminalStatuses:
    @pytest.mark.parametrize("status", [ReferralStatus.REJECTED, ReferralStatus.SCHEDULED])
    def test_terminal_status_has_no_allowed_targets(self, status):
        assert ALLOWED_TRANSITIONS[status] == frozenset()

    @pytest.mark.parametrize("status", [ReferralStatus.REJECTED, ReferralStatus.SCHEDULED])
    def test_nothing_can_leave_a_terminal_status(self, status):
        for target in ALL_STATUSES:
            assert is_valid_transition(status, target) is False


class TestNewStatus:
    def test_new_can_only_move_to_in_review(self):
        assert ALLOWED_TRANSITIONS[ReferralStatus.NEW] == frozenset({ReferralStatus.IN_REVIEW})

    def test_new_cannot_skip_straight_to_a_later_status(self):
        assert is_valid_transition(ReferralStatus.NEW, ReferralStatus.ACCEPTED) is False
        assert is_valid_transition(ReferralStatus.NEW, ReferralStatus.SCHEDULED) is False
        assert is_valid_transition(ReferralStatus.NEW, ReferralStatus.REJECTED) is False


class TestInReviewStatus:
    def test_in_review_can_branch_to_accepted_or_rejected(self):
        assert ALLOWED_TRANSITIONS[ReferralStatus.IN_REVIEW] == frozenset(
            {ReferralStatus.ACCEPTED, ReferralStatus.REJECTED}
        )

    def test_in_review_cannot_skip_straight_to_scheduled(self):
        assert is_valid_transition(ReferralStatus.IN_REVIEW, ReferralStatus.SCHEDULED) is False
