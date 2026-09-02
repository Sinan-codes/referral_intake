"""Duplicate detection: groups referrals likely to be the same patient.

Referrals arrive from three independent sources with no shared patient
identifier, so duplicates have to be inferred from demographics. The match
key is (last name, date of birth) -- deliberately NOT full name:

- DOB is the one field precise enough that two unrelated patients sharing it
  is rare enough to accept as the matching signal.
- First name is left out on purpose. A nickname or spelling variant ("Bob"
  vs "Robert") is common across independently-filled-out sources and would
  hide an otherwise-exact match if the full name had to agree. The seed data
  has exactly this case (a web_form "Bob Barnhardt" and "Robert Barnhardt",
  same DOB) with no more information than the two records themselves.

The cost of dropping first name is accepted, documented false positives:
two different patients who share a last name and DOB would be grouped
together. That's judged rarer and less risky in a referral-intake context
than silently missing a real duplicate.

A referral with no last name or no date of birth can't be matched at all
and is left out of every group -- guessing would be worse than not flagging
it.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.models.referral import Referral

MatchKey = tuple[str, date]


def match_key(referral: Referral) -> MatchKey | None:
    """The (last name, date of birth) key used to group referrals, or None
    if the referral doesn't have enough demographic data to match on."""

    last_name = (referral.patient_name.last_name or "").strip().lower()
    date_of_birth = referral.date_of_birth
    if not last_name or date_of_birth is None:
        return None
    return (last_name, date_of_birth)


def duplicate_group_id(key: MatchKey) -> str:
    # Deterministic and stable, matching the `f"{source}:{id}"` convention
    # used for referral IDs -- not a random UUID.
    last_name, date_of_birth = key
    return f"dup:{last_name}:{date_of_birth.isoformat()}"


def find_duplicate_groups(referrals: list[Referral]) -> dict[str, list[Referral]]:
    """Group referrals sharing a match key, keyed by `duplicate_group_id`.

    Groups of size 1 are dropped -- a referral with no match isn't a
    duplicate of itself.
    """

    by_key: dict[MatchKey, list[Referral]] = defaultdict(list)
    for referral in referrals:
        key = match_key(referral)
        if key is not None:
            by_key[key].append(referral)

    return {
        duplicate_group_id(key): group for key, group in by_key.items() if len(group) > 1
    }


def apply_duplicate_groups(referrals: list[Referral]) -> list[Referral]:
    """Return referrals with `duplicate_group_id` set for every referral
    that has at least one match.

    Returns new `Referral` instances (via `model_copy`) rather than mutating
    in place, so callers holding the original list aren't surprised.
    Referrals with no match are returned as-is.
    """

    groups = find_duplicate_groups(referrals)
    group_id_by_referral_id = {
        referral.id: group_id for group_id, group in groups.items() for referral in group
    }

    return [
        referral.model_copy(update={"duplicate_group_id": group_id_by_referral_id[referral.id]})
        if referral.id in group_id_by_referral_id
        else referral
        for referral in referrals
    ]
