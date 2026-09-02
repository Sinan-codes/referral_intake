"""Loads the seed file and runs every per-source normalizer against it.

The three sources fail independently: a normalizer that can't handle a given
efax record doesn't stop ehr_fhir or web_form from being processed, and one
source's records don't need to see another's.
"""

from __future__ import annotations

from pathlib import Path

from app.models.raw import ReferralsSeedFile
from app.models.referral import Referral
from app.normalization.common import NormalizationError
from app.normalization.efax import normalize_efax_records
from app.normalization.ehr_fhir import normalize_fhir_records
from app.normalization.web_form import normalize_web_form_records

DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "seed" / "referrals-seed.json"


def load_seed_file(path: Path = DEFAULT_SEED_PATH) -> ReferralsSeedFile:
    return ReferralsSeedFile.model_validate_json(path.read_text())


def normalize_all(seed: ReferralsSeedFile) -> tuple[list[Referral], list[NormalizationError]]:
    """Run every source's normalizer and merge the results."""

    efax_referrals, efax_errors = normalize_efax_records(seed.sources.efax.records)
    fhir_referrals, fhir_errors = normalize_fhir_records(seed.sources.ehr_fhir.records)
    web_referrals, web_errors = normalize_web_form_records(seed.sources.web_form.records)

    referrals = [*efax_referrals, *fhir_referrals, *web_referrals]
    errors = [*efax_errors, *fhir_errors, *web_errors]
    return referrals, errors


def normalize_seed_file(
    path: Path = DEFAULT_SEED_PATH,
) -> tuple[list[Referral], list[NormalizationError]]:
    """Convenience wrapper: load the seed file from disk, then normalize it."""

    return normalize_all(load_seed_file(path))
