"""Ingests seed data into the CDSS's two new Pinecone namespaces:
`clinical-guidelines` (for the Guideline agent + Alternative Therapy agent)
and `contraindications` (for the Contraindication agent), using OpenRouter
for embeddings.

Usage:
    python -m scripts.ingest_cdss_namespaces

Requires OPENROUTER_API_KEY and PINECONE_API_KEY. The Pinecone index must
already exist (same index as the drug-interaction data -- namespaces live
inside one index, they don't need separate indexes).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.documents import Document  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.pinecone_service import build_vector_store  # noqa: E402

configure_logging()
logger = get_logger(__name__)


# --- clinical-guidelines namespace -----------------------------------------
# A small illustrative set of first-line treatment recommendations. In
# production this would be sourced from a licensed guideline database
# (e.g. UpToDate, NICE, JNC-8/ACC-AHA) and ingested in bulk.
GUIDELINE_SEEDS: list[dict] = [
    {
        "id": "guideline-hypertension",
        "diagnosis": "essential hypertension",
        "text": "First-line treatment for essential hypertension includes ACE inhibitors, "
        "ARBs, calcium channel blockers, or thiazide diuretics.",
        "recommendation": "ACE inhibitors, ARBs, calcium channel blockers, or thiazide diuretics are first-line.",
        "guideline_section": "ACC/AHA 2017 Hypertension Guideline",
    },
    {
        "id": "guideline-alternative-nsaid",
        "diagnosis": "pain management with anticoagulant use",
        "text": "For patients on anticoagulant therapy needing pain relief, acetaminophen "
        "is the preferred alternative to NSAIDs, which increase bleeding risk.",
        "recommendation": "Acetaminophen is preferred over NSAIDs for pain relief in anticoagulated patients.",
        "guideline_section": "ACCP Antithrombotic Guidelines",
    },
    {
        "id": "guideline-type2-diabetes",
        "diagnosis": "type 2 diabetes mellitus",
        "text": "Metformin remains first-line pharmacologic therapy for type 2 diabetes, "
        "unless contraindicated by renal impairment.",
        "recommendation": "Metformin first-line unless eGFR is significantly reduced.",
        "guideline_section": "ADA Standards of Care",
    },
    {
        "id": "guideline-uti",
        "diagnosis": "uncomplicated urinary tract infection",
        "text": "Nitrofurantoin or trimethoprim-sulfamethoxazole are first-line for "
        "uncomplicated UTIs in patients without contraindications.",
        "recommendation": "Nitrofurantoin or TMP-SMX first-line for uncomplicated UTI.",
        "guideline_section": "IDSA UTI Guidelines",
    },
]

# --- contraindications namespace --------------------------------------------
# Drug-vs-condition contraindications (distinct from drug-vs-drug
# interactions, which live in the default namespace).
CONTRAINDICATION_SEEDS: list[dict] = [
    {
        "id": "contraindication-ibuprofen-warfarin",
        "drug_name": "Ibuprofen",
        "condition": "warfarin",
        "severity": "high",
        "text": "Ibuprofen and other NSAIDs are contraindicated in patients on warfarin "
        "due to significantly increased bleeding risk.",
        "explanation": "NSAIDs increase bleeding risk in patients on anticoagulant therapy.",
        "guideline_section": "ACCP Antithrombotic Guidelines",
    },
    {
        "id": "contraindication-metformin-renal",
        "drug_name": "Metformin",
        "condition": "chronic kidney disease",
        "severity": "high",
        "text": "Metformin is contraindicated or requires dose reduction in patients with "
        "significant chronic kidney disease due to lactic acidosis risk.",
        "explanation": "Reduced renal clearance increases lactic acidosis risk.",
        "guideline_section": "ADA Standards of Care",
    },
    {
        "id": "contraindication-lisinopril-pregnancy",
        "drug_name": "Lisinopril",
        "condition": "pregnancy",
        "severity": "critical",
        "text": "ACE inhibitors like lisinopril are contraindicated in pregnancy due to "
        "risk of fetal renal damage and other teratogenic effects.",
        "explanation": "ACE inhibitors are teratogenic and harm fetal renal development.",
        "guideline_section": "ACOG Practice Bulletin",
    },
]


def _build_guideline_documents() -> tuple[list[Document], list[str]]:
    documents = [
        Document(
            page_content=seed["text"],
            metadata={
                "diagnosis": seed["diagnosis"],
                "recommendation": seed["recommendation"],
                "guideline_section": seed["guideline_section"],
            },
        )
        for seed in GUIDELINE_SEEDS
    ]
    ids = [seed["id"] for seed in GUIDELINE_SEEDS]
    return documents, ids


def _build_contraindication_documents() -> tuple[list[Document], list[str]]:
    documents = [
        Document(
            page_content=seed["text"],
            metadata={
                "drug_name": seed["drug_name"],
                "drug_name_lower": seed["drug_name"].strip().lower(),
                "condition": seed["condition"],
                "severity": seed["severity"],
                "explanation": seed["explanation"],
                "guideline_section": seed["guideline_section"],
            },
        )
        for seed in CONTRAINDICATION_SEEDS
    ]
    ids = [seed["id"] for seed in CONTRAINDICATION_SEEDS]
    return documents, ids


def main() -> None:
    settings = get_settings()
    settings.validate_for_ingestion()

    guideline_store = build_vector_store(settings, namespace="clinical-guidelines")
    guideline_docs, guideline_ids = _build_guideline_documents()
    guideline_store.add_documents(documents=guideline_docs, ids=guideline_ids)
    logger.info("guidelines_ingested", extra={"extra_fields": {"count": len(guideline_docs)}})
    print(f"Upserted {len(guideline_docs)} records into namespace 'clinical-guidelines'.")

    contraindication_store = build_vector_store(settings, namespace="contraindications")
    contraindication_docs, contraindication_ids = _build_contraindication_documents()
    contraindication_store.add_documents(documents=contraindication_docs, ids=contraindication_ids)
    logger.info("contraindications_ingested", extra={"extra_fields": {"count": len(contraindication_docs)}})
    print(f"Upserted {len(contraindication_docs)} records into namespace 'contraindications'.")


if __name__ == "__main__":
    main()
