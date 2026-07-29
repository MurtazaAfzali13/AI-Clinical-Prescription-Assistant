import pytest

from app.models.schemas import Medication, PatientInfo, PrescriptionExtraction


@pytest.fixture
def sample_extraction() -> PrescriptionExtraction:
    return PrescriptionExtraction(
        patient=PatientInfo(name="John Doe", age=34, record_no="REC-001"),
        diagnosis="Common cold with mild fever",
        medications=[
            Medication(name="Acetaminophen", dosage="500mg", frequency="twice a day", duration="5 days"),
            Medication(name="Warfarin", dosage="5mg", frequency="once a day", duration="10 days"),
        ],
        advice="Rest, drink fluids, follow up if fever persists beyond 3 days.",
    )
