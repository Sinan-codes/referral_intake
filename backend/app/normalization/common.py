"""Small helpers shared by the per-source normalizers.

Each source (efax, ehr_fhir, web_form) has its own field names and quirks,
but the fixes for "this string is blank", "this name arrived ALL CAPS", and
"we couldn't read the urgency" are identical everywhere -- kept here once
instead of copy-pasted per source.
"""

from __future__ import annotations

from app.models.referral import Urgency


class NormalizationError(ValueError):
    """Raised when a raw record is missing data no amount of defaulting can fill in."""

    def __init__(self, source: str, record_id: str, reason: str) -> None:
        super().__init__(f"{source} record {record_id}: {reason}")
        self.source = source
        self.record_id = record_id


# A source's urgency signal can be missing or unrecognized. We escalate
# rather than default to routine: in a behavioral-health queue, silently
# downgrading a referral whose urgency we simply failed to read is the worse
# failure mode -- a human reviewing it as `stat` costs a minute, a missed
# `stat` read as `routine` can cost a lot more.
UNKNOWN_PRIORITY_FALLBACK = Urgency.STAT


def clean(value: str | None) -> str | None:
    """Blank/whitespace-only strings become None -- "" and "unknown" shouldn't differ."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_name_casing(name: str) -> str:
    # Some sources yield ALL-CAPS names (OCR, or FHIR `display` fields);
    # leave already-mixed-case names untouched rather than reformatting them.
    return name.title() if name.isupper() else name
