"""Duplicate detection: groups referrals likely to be the same patient.

Referrals arrive from three independent sources with no shared patient
identifier, so duplicates have to be inferred from demographics. The
baseline match key is (last name, date of birth) -- deliberately NOT full
name:

- DOB is the one field precise enough that two unrelated patients sharing it
  is rare enough to accept as the matching signal. Loosening DOB too (in
  addition to last name) was considered and rejected for the same reason
  it was chosen as the anchor in the first place: it's the one field with
  low collision risk. Fuzzing both fields at once multiplies the
  false-positive surface instead of shifting it.
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

**Fuzzy tier (OCR tolerance).** `efax` is OCR output, and OCR occasionally
misreads a single character in a name ("Okonkwo" -> "Okonkvo"). Under a
strict exact match, that one-character slip puts the two referrals in
different hash buckets and a real duplicate silently never gets flagged --
the exact rule's worst failure mode (see the README). To catch this without
opening the door to unrelated false positives, referrals additionally match
when, for the same date of birth, their last names are within Levenshtein
edit distance 1 of each other AND at least one of the two is
`efax`-sourced. `ehr_fhir` and `web_form` are structured, typed data, not
scanned, so a pair of two non-efax referrals still requires an exact
last-name match -- the fuzzy tier only opens up where OCR noise can
actually originate. This is deliberately narrow: it does not catch
multi-character misreads, DOB transcription errors, or name errors from a
non-efax source -- all still silent false negatives after this change (see
the README).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.models.referral import Referral, ReferralSource

MatchKey = tuple[str, date]

# A single OCR-misread character is the failure mode this tier targets --
# not a general fuzzy-name matcher. Keep this at 1; raising it starts
# trading real precision for speculative recall (see README).
_FUZZY_LAST_NAME_MAX_DISTANCE = 1


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


def _levenshtein_distance(a: str, b: str) -> int:
    """Plain Levenshtein edit distance (insertion, deletion, substitution).

    No transposition (Damerau-Levenshtein): a single OCR misread swaps one
    character's shape for another's, or drops/adds a stray mark -- it
    doesn't reorder two correct characters the way a typing typo does.
    Plain Levenshtein already covers the error shapes OCR actually
    produces, so the extra bookkeeping isn't worth it here.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i]
        for j, char_b in enumerate(b, start=1):
            current_row.append(
                min(
                    current_row[j - 1] + 1,
                    previous_row[j] + 1,
                    previous_row[j - 1] + (char_a != char_b),
                )
            )
        previous_row = current_row
    return previous_row[-1]


def _last_names_are_close(a: str, b: str) -> bool:
    """True if `a` and `b` are within one edit -- the shape of a single
    OCR-misread character."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > _FUZZY_LAST_NAME_MAX_DISTANCE:
        return False  # can't be within 1 edit if lengths differ by more than 1
    return _levenshtein_distance(a, b) <= _FUZZY_LAST_NAME_MAX_DISTANCE


class _UnionFind:
    """Minimal disjoint-set over referral IDs, path compression only.

    ~40 seed records: no need for union-by-rank on top of path compression,
    and no reason to reach for a dependency for this.
    """

    def __init__(self, ids: list[str]) -> None:
        self._parent: dict[str, str] = {id_: id_ for id_ in ids}

    def find(self, x: str) -> str:
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:  # path compression
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_b] = root_a


def find_duplicate_groups(referrals: list[Referral]) -> dict[str, list[Referral]]:
    """Group referrals that are likely the same patient, keyed by
    `duplicate_group_id`.

    Two tiers, unioned together (a referral can end up in a group via
    either tier, or both):

    1. Exact: same (last name, date of birth).
    2. Fuzzy: same date of birth, last names within one edit of each other,
       and at least one referral is `efax`-sourced (see module docstring).

    Groups of size 1 are dropped -- a referral with no match isn't a
    duplicate of itself. Groups are connected components, so matching is
    transitive: if A fuzzy-matches B and B fuzzy-matches C, all three land
    in one group even if A and C aren't within one edit of each other
    directly. That's intentional -- it's the same transitivity an exact
    3-way group already relies on, just reached through a chain of single
    typos instead of one shared spelling.
    """

    keyed = [(referral, match_key(referral)) for referral in referrals]
    matchable = [(referral, key) for referral, key in keyed if key is not None]
    if not matchable:
        return {}

    union_find = _UnionFind([referral.id for referral, _key in matchable])

    # Tier 1: exact match -- union every referral sharing a key.
    by_exact_key: dict[MatchKey, list[Referral]] = defaultdict(list)
    for referral, key in matchable:
        by_exact_key[key].append(referral)
    for group in by_exact_key.values():
        first_id = group[0].id
        for referral in group[1:]:
            union_find.union(first_id, referral.id)

    # Tier 2: fuzzy match -- same DOB, last names within one edit, at least
    # one side efax. Bucketing by DOB keeps this well short of O(n^2) over
    # all referrals; a DOB bucket is at most a handful of records here.
    by_dob: dict[date, list[tuple[Referral, str]]] = defaultdict(list)
    for referral, (last_name, date_of_birth) in matchable:
        by_dob[date_of_birth].append((referral, last_name))
    for bucket in by_dob.values():
        for i in range(len(bucket)):
            referral_a, last_a = bucket[i]
            for referral_b, last_b in bucket[i + 1 :]:
                if last_a == last_b:
                    continue  # already unioned exactly, above
                if ReferralSource.EFAX not in (referral_a.source, referral_b.source):
                    continue  # fuzzy tier only applies where OCR noise originates
                if _last_names_are_close(last_a, last_b):
                    union_find.union(referral_a.id, referral_b.id)

    components: dict[str, list[Referral]] = defaultdict(list)
    for referral, _key in matchable:
        components[union_find.find(referral.id)].append(referral)

    keys_by_id = {referral.id: key for referral, key in matchable}
    groups: dict[str, list[Referral]] = {}
    for members in components.values():
        if len(members) < 2:
            continue
        # min() picks whichever (last_name, dob) pair sorts first --
        # arbitrary but deterministic, and identical to today's behavior
        # when a group has only one distinct key (the exact-only case).
        # Note: within one component, dob is always identical across
        # members (every union edge, exact or fuzzy, only ever connects
        # referrals sharing a DOB), so this reduces to "smallest spelling".
        canonical_key = min(keys_by_id[member.id] for member in members)
        groups[duplicate_group_id(canonical_key)] = members

    return groups


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
