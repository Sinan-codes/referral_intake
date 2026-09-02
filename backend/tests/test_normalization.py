"""Tests for the per-source normalizers in `app.normalization`.

Each source is tested for: the happy path, the one truly-required field
raising `NormalizationError` when unusable, and the source-specific
translation quirks (name casing/splitting, priority/urgency mapping,
timestamp parsing, blank-string cleaning) called out in the normalizer
docstrings.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.models.raw import (
    EfaxPatient,
    EfaxRecord,
    FhirReasonCode,
    FhirServiceRequest,
    FhirSubject,
    WebFormRecord,
)
from app.models.referral import ReferralSource, Urgency
from app.normalization.common import NormalizationError
from app.normalization.efax import normalize_efax_record, normalize_efax_records
from app.normalization.ehr_fhir import normalize_fhir_record, normalize_fhir_records
from app.normalization.web_form import normalize_web_form_record, normalize_web_form_records


# --- efax ----------------------------------------------------------------------


def _efax_record(**overrides) -> EfaxRecord:
    defaults = dict(
        id="efax-1",
        received_ts=1_700_000_000,
        patient=EfaxPatient(full_name="GRACE DELACROIX", dob="03/14/1960"),
        referring_provider="Dr. Smith",
        reason_free_text="follow-up",
        priority="STAT",
    )
    defaults.update(overrides)
    return EfaxRecord(**defaults)


class TestNormalizeEfaxRecord:
    def test_happy_path(self):
        referral = normalize_efax_record(_efax_record())

        assert referral.id == "efax:efax-1"
        assert referral.source == ReferralSource.EFAX
        assert referral.source_record_id == "efax-1"
        assert referral.received_at == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)
        assert referral.date_of_birth == date(1960, 3, 14)
        assert referral.referring_provider == "Dr. Smith"
        assert referral.reason == "follow-up"
        assert referral.urgency == Urgency.STAT

    def test_all_caps_name_is_title_cased_and_split(self):
        referral = normalize_efax_record(_efax_record(patient=EfaxPatient(full_name="GRACE DELACROIX")))

        assert referral.patient_name.raw_full_name == "Grace Delacroix"
        assert referral.patient_name.first_name == "Grace"
        assert referral.patient_name.last_name == "Delacroix"

    def test_mixed_case_name_is_left_untouched(self):
        referral = normalize_efax_record(_efax_record(patient=EfaxPatient(full_name="Grace Delacroix")))

        assert referral.patient_name.raw_full_name == "Grace Delacroix"

    def test_missing_patient_name_raises(self):
        with pytest.raises(NormalizationError):
            normalize_efax_record(_efax_record(patient=EfaxPatient(full_name=None)))

    def test_blank_patient_name_raises(self):
        with pytest.raises(NormalizationError):
            normalize_efax_record(_efax_record(patient=EfaxPatient(full_name="   ")))

    def test_unparseable_dob_degrades_to_none(self):
        referral = normalize_efax_record(
            _efax_record(patient=EfaxPatient(full_name="Grace Delacroix", dob="not-a-date"))
        )

        assert referral.date_of_birth is None

    def test_missing_dob_degrades_to_none(self):
        referral = normalize_efax_record(
            _efax_record(patient=EfaxPatient(full_name="Grace Delacroix", dob=None))
        )

        assert referral.date_of_birth is None

    def test_blank_referring_provider_becomes_none(self):
        referral = normalize_efax_record(_efax_record(referring_provider=""))

        assert referral.referring_provider is None

    def test_blank_reason_becomes_none(self):
        referral = normalize_efax_record(_efax_record(reason_free_text=""))

        assert referral.reason is None

    def test_known_priority_routine(self):
        referral = normalize_efax_record(_efax_record(priority="ROUTINE"))

        assert referral.urgency == Urgency.ROUTINE

    @pytest.mark.parametrize("priority", [None, "", "GARBLED", "urgent"])
    def test_unrecognized_or_missing_priority_escalates_to_stat(self, priority):
        referral = normalize_efax_record(_efax_record(priority=priority))

        assert referral.urgency == Urgency.STAT

    def test_single_word_name_has_no_last_name(self):
        referral = normalize_efax_record(_efax_record(patient=EfaxPatient(full_name="Prince")))

        assert referral.patient_name.first_name == "Prince"
        assert referral.patient_name.last_name is None


class TestNormalizeEfaxRecords:
    def test_batch_skips_bad_records_and_keeps_good_ones(self):
        good = _efax_record(id="good-1")
        bad = _efax_record(id="bad-1", patient=EfaxPatient(full_name=None))

        referrals, errors = normalize_efax_records([good, bad])

        assert len(referrals) == 1
        assert referrals[0].source_record_id == "good-1"
        assert len(errors) == 1
        assert errors[0].source == "efax"
        assert errors[0].record_id == "bad-1"


# --- ehr_fhir --------------------------------------------------------------------


def _fhir_record(**overrides) -> FhirServiceRequest:
    defaults = dict(
        resourceType="ServiceRequest",
        id="fhir-1",
        authoredOn="2024-01-15T10:30:00Z",
        subject=FhirSubject(display="RENTERÍA, MARGUERITE", birthDate="1953-01-13"),
        priority="routine",
    )
    defaults.update(overrides)
    return FhirServiceRequest(**defaults)


class TestNormalizeFhirRecord:
    def test_happy_path(self):
        referral = normalize_fhir_record(_fhir_record())

        assert referral.id == "ehr_fhir:fhir-1"
        assert referral.source == ReferralSource.EHR_FHIR
        assert referral.received_at == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert referral.date_of_birth == date(1953, 1, 13)
        assert referral.urgency == Urgency.ROUTINE

    def test_last_comma_first_display_is_reordered_and_title_cased(self):
        referral = normalize_fhir_record(_fhir_record(subject=FhirSubject(display="RENTERÍA, MARGUERITE")))

        assert referral.patient_name.first_name == "Marguerite"
        assert referral.patient_name.last_name == "Rentería"
        assert referral.patient_name.raw_full_name == "Marguerite Rentería"

    def test_display_without_comma_becomes_last_name_only(self):
        referral = normalize_fhir_record(_fhir_record(subject=FhirSubject(display="MADONNA")))

        assert referral.patient_name.first_name is None
        assert referral.patient_name.last_name == "Madonna"

    def test_missing_subject_raises(self):
        with pytest.raises(NormalizationError):
            normalize_fhir_record(_fhir_record(subject=None))

    def test_blank_display_raises(self):
        with pytest.raises(NormalizationError):
            normalize_fhir_record(_fhir_record(subject=FhirSubject(display="   ")))

    def test_missing_authored_on_raises(self):
        with pytest.raises(NormalizationError):
            normalize_fhir_record(_fhir_record(authoredOn=None))

    def test_unparseable_authored_on_raises(self):
        with pytest.raises(NormalizationError):
            normalize_fhir_record(_fhir_record(authoredOn="not-a-timestamp"))

    def test_missing_birth_date_degrades_to_none(self):
        referral = normalize_fhir_record(
            _fhir_record(subject=FhirSubject(display="A, B", birthDate=None))
        )

        assert referral.date_of_birth is None

    def test_first_reason_code_text_is_used(self):
        referral = normalize_fhir_record(
            _fhir_record(reasonCode=[FhirReasonCode(text="chronic pain")])
        )

        assert referral.reason == "chronic pain"

    def test_missing_reason_code_degrades_to_none(self):
        referral = normalize_fhir_record(_fhir_record(reasonCode=None))

        assert referral.reason is None

    @pytest.mark.parametrize(
        ("raw_priority", "expected"),
        [
            ("routine", Urgency.ROUTINE),
            ("urgent", Urgency.URGENT),
            ("asap", Urgency.STAT),
            ("stat", Urgency.STAT),
            ("ROUTINE", Urgency.ROUTINE),
        ],
    )
    def test_priority_vocabulary_mapping(self, raw_priority, expected):
        referral = normalize_fhir_record(_fhir_record(priority=raw_priority))

        assert referral.urgency == expected

    @pytest.mark.parametrize("priority", [None, "unknown"])
    def test_unrecognized_or_missing_priority_escalates_to_stat(self, priority):
        referral = normalize_fhir_record(_fhir_record(priority=priority))

        assert referral.urgency == Urgency.STAT


class TestNormalizeFhirRecords:
    def test_batch_skips_bad_records_and_keeps_good_ones(self):
        good = _fhir_record(id="good-1")
        bad = _fhir_record(id="bad-1", authoredOn=None)

        referrals, errors = normalize_fhir_records([good, bad])

        assert len(referrals) == 1
        assert referrals[0].source_record_id == "good-1"
        assert len(errors) == 1
        assert errors[0].record_id == "bad-1"


# --- web_form --------------------------------------------------------------------


def _web_form_record(**overrides) -> WebFormRecord:
    defaults = dict(
        submissionId="web-1",
        submittedAt="2024-01-15T03:30:00-07:00",
        firstName="Jane",
        lastName="Doe",
        dateOfBirth="1990-05-01",
        referredBy="Family member",
        notes="please schedule soon",
        urgent=True,
    )
    defaults.update(overrides)
    return WebFormRecord(**defaults)


class TestNormalizeWebFormRecord:
    def test_happy_path(self):
        referral = normalize_web_form_record(_web_form_record())

        assert referral.id == "web_form:web-1"
        assert referral.source == ReferralSource.WEB_FORM
        assert referral.patient_name.first_name == "Jane"
        assert referral.patient_name.last_name == "Doe"
        assert referral.patient_name.raw_full_name == "Jane Doe"
        assert referral.date_of_birth == date(1990, 5, 1)
        assert referral.referring_provider == "Family member"
        assert referral.reason == "please schedule soon"
        assert referral.urgency == Urgency.URGENT

    def test_offset_timestamp_is_converted_to_utc(self):
        referral = normalize_web_form_record(_web_form_record(submittedAt="2024-01-15T03:30:00-07:00"))

        assert referral.received_at == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)

    def test_urgent_false_maps_to_routine(self):
        referral = normalize_web_form_record(_web_form_record(urgent=False))

        assert referral.urgency == Urgency.ROUTINE

    def test_urgent_true_maps_to_urgent_never_stat(self):
        referral = normalize_web_form_record(_web_form_record(urgent=True))

        assert referral.urgency == Urgency.URGENT

    def test_missing_both_names_raises(self):
        with pytest.raises(NormalizationError):
            normalize_web_form_record(_web_form_record(firstName=None, lastName=None))

    def test_only_first_name_present_is_sufficient(self):
        referral = normalize_web_form_record(_web_form_record(firstName="Jane", lastName=None))

        assert referral.patient_name.raw_full_name == "Jane"
        assert referral.patient_name.last_name is None

    def test_blank_submitted_at_raises(self):
        with pytest.raises(NormalizationError):
            normalize_web_form_record(_web_form_record(submittedAt=""))

    def test_unparseable_submitted_at_raises(self):
        with pytest.raises(NormalizationError):
            normalize_web_form_record(_web_form_record(submittedAt="not-a-timestamp"))

    def test_empty_notes_string_becomes_none(self):
        referral = normalize_web_form_record(_web_form_record(notes=""))

        assert referral.reason is None

    def test_missing_dob_degrades_to_none(self):
        referral = normalize_web_form_record(_web_form_record(dateOfBirth=None))

        assert referral.date_of_birth is None

    def test_all_caps_name_parts_are_title_cased(self):
        referral = normalize_web_form_record(_web_form_record(firstName="JANE", lastName="DOE"))

        assert referral.patient_name.first_name == "Jane"
        assert referral.patient_name.last_name == "Doe"


class TestNormalizeWebFormRecords:
    def test_batch_skips_bad_records_and_keeps_good_ones(self):
        good = _web_form_record(submissionId="good-1")
        bad = _web_form_record(submissionId="bad-1", firstName=None, lastName=None)

        referrals, errors = normalize_web_form_records([good, bad])

        assert len(referrals) == 1
        assert referrals[0].source_record_id == "good-1"
        assert len(errors) == 1
        assert errors[0].record_id == "bad-1"
