from app.tools.dose_calculator import calculate_dose, parse_dose_mg


def test_parse_dose_mg_extracts_number():
    assert parse_dose_mg("500mg") == 500.0
    assert parse_dose_mg("5 mg") == 5.0
    assert parse_dose_mg("2.5mg") == 2.5


def test_parse_dose_mg_returns_none_for_unparseable():
    assert parse_dose_mg("as needed") is None
    assert parse_dose_mg("") is None


def test_calculate_dose_within_range():
    result = calculate_dose("Amlodipine", "5mg")
    assert result["is_within_range"] is True
    assert result["renal_adjustment_applied"] is False


def test_calculate_dose_exceeds_max():
    result = calculate_dose("Amlodipine", "20mg")
    assert result["is_within_range"] is False
    assert "exceeds" in result["explanation"]


def test_calculate_dose_below_min():
    result = calculate_dose("Simvastatin", "2mg")
    assert result["is_within_range"] is False
    assert "below" in result["explanation"]


def test_calculate_dose_applies_renal_adjustment_when_egfr_low():
    # Losartan's normal max is 100mg, but drops to 50mg when eGFR < 30.
    result = calculate_dose("Losartan", "75mg", egfr=25)
    assert result["renal_adjustment_applied"] is True
    assert result["recommended_max_mg"] == 50
    assert result["is_within_range"] is False


def test_calculate_dose_no_renal_adjustment_when_egfr_normal():
    result = calculate_dose("Losartan", "75mg", egfr=90)
    assert result["renal_adjustment_applied"] is False
    assert result["recommended_max_mg"] == 100
    assert result["is_within_range"] is True


def test_calculate_dose_unknown_drug():
    result = calculate_dose("Unobtainium", "10mg")
    assert result["is_within_range"] is None
    assert "No reference dosing range" in result["explanation"]


def test_calculate_dose_unparseable_dosage_text():
    result = calculate_dose("Amlodipine", "as needed")
    assert result["prescribed_dose_mg"] is None
    assert result["is_within_range"] is None
