import math
import pytest
from pydantic import ValidationError
from app.models.user import UserCreate, UserUpdate
from app.models.telemetry import Vitals, WaveformBatch
from app.adapters.bidmc import BIDMCDatasetAdapter
from app.models.contact import normalize_phone
from app.security import hash_password, verify_password
from app.services.telemetry_service import summarize
from app.services.simulation_service import Simulation


@pytest.mark.parametrize('raw,expected', [('9876543210', '+919876543210'), ('+44 20 7946 0018', '+442079460018'), ('011 2345 6789', '+911123456789')])
def test_international_and_indian_landline_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize('raw', ['123', '+910000000000', 'not a phone'])
def test_invalid_phone_is_rejected(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_profile_fields_and_partial_update():
    user = UserCreate(email='PERSON@example.com', password='long-enough-password', full_name=' Test Person ',
        phone='9876543210', additional_phones=['+44 20 7946 0018'], address='Test address')
    assert user.phone == '+919876543210'
    assert user.address == 'Test address'
    assert user.additional_phones == ['+442079460018']
    assert UserUpdate(full_name='New Name').model_dump(exclude_unset=True) == {'full_name': 'New Name'}


def test_future_birthdate_and_short_password_rejected():
    with pytest.raises(ValidationError):
        UserUpdate(date_of_birth='2999-01-01')
    with pytest.raises(ValidationError):
        UserCreate(email='test@example.com', password='short', full_name='Test')


def test_argon2_password_roundtrip():
    password = 'long password ' + '\u00e9' * 60
    hashed = hash_password(password)
    assert hashed.startswith('$argon2id$')
    assert verify_password(password, hashed)
    assert not verify_password('wrong', hashed)


def test_missing_and_invalid_metrics():
    assert Vitals(heart_rate=72).temperature is None
    with pytest.raises(ValidationError):
        Vitals(spo2=101)
    with pytest.raises(ValidationError):
        Vitals(heart_rate=float('nan'))


def test_persistent_deviation_requires_baseline_and_continuity():
    baseline = [{'second': i, 'vitals': {'heart_rate': 72 + math.sin(i)}} for i in range(60)]
    abnormal = [{'second': i, 'vitals': {'heart_rate': 110}} for i in range(60, 90)]
    assert summarize(baseline[:20])['contributors'] == []
    assert summarize(baseline + abnormal)['contributors']
    abnormal[-1]['second'] = 100
    assert summarize(baseline + abnormal)['contributors'] == []


def test_simulator_determinism_and_gradual_transition():
    first, second = Simulation('test'), Simulation('test')
    assert first.sample().vitals == second.sample().vitals
    first.scenario = 'RUNNING'
    before = first.values[:]
    packet = first.sample()
    assert 0 < packet.vitals.heart_rate - before[0] < 5
    assert packet.vitals.respiratory_rate > before[2]
    assert packet.source_type.value == 'SYNTHETIC_SIMULATOR'


def test_missing_waveform_samples_preserve_timing():
    adapter = BIDMCDatasetAdapter()
    rows = [{'Time [s]': str(i * 0.008), 'PLETH': value} for i, value in enumerate(['1', '', '3'])]
    packet = adapter._normalize_batch('bidmc_01', 'test', rows, [0.0], [Vitals(heart_rate=72)])
    assert packet.waveforms.ppg == [1, None, 3]
    assert packet.waveforms.ecg == [None, None, None]
    with pytest.raises(ValidationError):
        WaveformBatch(sample_rate_hz=125, sample_interval_ms=8, start_offset_seconds=0, ppg=[float('inf')])


def test_missing_metric_or_low_quality_cannot_claim_sustained_deviation():
    rows = [{'second': i, 'vitals': {'heart_rate': 72 + math.sin(i) if i < 60 else 110}} for i in range(90)]
    assert summarize(rows)['contributors']
    rows[-5]['vitals']['heart_rate'] = None
    assert not summarize(rows)['contributors']
    rows[-5]['vitals']['heart_rate'] = 110
    rows[-5]['signal_quality'] = 0.4
    assert not summarize(rows)['contributors']
