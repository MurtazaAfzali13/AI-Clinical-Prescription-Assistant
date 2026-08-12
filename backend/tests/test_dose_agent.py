from app.agents.cdss_state import create_initial_cdss_state
from app.agents.dose_agent import dose_node
from app.models.cdss_schemas import LabContext
from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction


def test_dose_node_checks_each_medication():
    extraction = PrescriptionExtraction(
        patient=PatientInfo(),
        diagnosis="Essential hypertension",
        medications=[
            Medication(name="Amlodipine", dosage="5mg", frequency="once daily"),
            Medication(name="Losartan", dosage="50mg", frequency="once daily"),
        ],
    )
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = extraction

    result = dose_node(state)

    assert len(result["dose_results"]) == 2
    assert result["dose_results"][0].medication_name == "Amlodipine"
    assert result["dose_results"][0].is_within_range is True


def test_dose_node_uses_lab_context_for_renal_adjustment():
    extraction = PrescriptionExtraction(
        patient=PatientInfo(),
        diagnosis="Essential hypertension",
        medications=[Medication(name="Losartan", dosage="75mg", frequency="once daily")],
    )
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = extraction
    state["lab_context"] = LabContext(weight_kg=70, age=60, egfr=25, liver_panel_normal=True)

    result = dose_node(state)

    assert result["dose_results"][0].renal_adjustment_applied is True
    assert result["dose_results"][0].is_within_range is False


def test_dose_node_no_extraction_returns_empty():
    state = create_initial_cdss_state("note", PatientInfo(), "t1", use_copilot_mode=True)
    state["extraction"] = None

    result = dose_node(state)

    assert result["dose_results"] == []
