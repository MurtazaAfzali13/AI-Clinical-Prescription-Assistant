"""Ingests a seed drug-interaction dataset into the Pinecone index used by
the Safety Checker agent, using OpenRouter for embeddings.

Usage:
    python -m scripts.ingest_drug_interactions

Requires OPENROUTER_API_KEY and PINECONE_API_KEY to be set (via .env or the
environment). The Pinecone index must already exist (create it in the
Pinecone console with a dimension matching EMBEDDING_MODEL, e.g. 1536 for
text-embedding-3-small) before running this script.
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

# A small illustrative seed set. In production this would be sourced from a
# licensed drug-interaction database (e.g. DrugBank, First Databank) and
# ingested in bulk.
SEED_INTERACTIONS: list[dict] = [
    {
        "id": "acetaminophen-warfarin",
        "drug_name": "Acetaminophen",
        "interacts_with": ["warfarin"],
        "severity": "high",
        "explanation": "Regular acetaminophen use can potentiate warfarin's anticoagulant "
        "effect, increasing bleeding risk.",
    },
    {
        "id": "ibuprofen-warfarin",
        "drug_name": "Ibuprofen",
        "interacts_with": ["warfarin"],
        "severity": "critical",
        "explanation": "NSAIDs combined with warfarin significantly increase the risk of "
        "gastrointestinal bleeding.",
    },
    {
        "id": "amoxicillin-warfarin",
        "drug_name": "Amoxicillin",
        "interacts_with": ["warfarin"],
        "severity": "moderate",
        "explanation": "Amoxicillin may enhance the anticoagulant effect of warfarin; monitor INR.",
    },
    {
        "id": "sildenafil-nitrates",
        "drug_name": "Sildenafil",
        "interacts_with": ["nitroglycerin", "isosorbide"],
        "severity": "critical",
        "explanation": "Combining PDE5 inhibitors with nitrates can cause severe, "
        "life-threatening hypotension.",
    },
    {
        "id": "metformin-contrast",
        "drug_name": "Metformin",
        "interacts_with": ["iodinated contrast"],
        "severity": "high",
        "explanation": "Risk of lactic acidosis when metformin is combined with iodinated "
        "contrast media in patients with renal impairment.",
    },
    {
        "id": "simvastatin-clarithromycin",
        "drug_name": "Simvastatin",
        "interacts_with": ["clarithromycin"],
        "severity": "high",
        "explanation": "CYP3A4 inhibition by clarithromycin raises simvastatin levels, "
        "increasing myopathy/rhabdomyolysis risk.",
    },
    {
        "id": "lisinopril-potassium",
        "drug_name": "Lisinopril",
        "interacts_with": ["potassium chloride", "spironolactone"],
        "severity": "moderate",
        "explanation": "ACE inhibitors combined with potassium-sparing agents can cause "
        "hyperkalemia.",
    },
]


def _build_documents(records: list[dict]) -> list[Document]:
    documents: list[Document] = []
    for record in records:
        text = (
            f"{record['drug_name']} interacts with {', '.join(record['interacts_with'])}: "
            f"{record['explanation']}"
        )
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "drug_name": record["drug_name"],
                    "drug_name_lower": record["drug_name"].strip().lower(),
                    "interacts_with": [d.lower() for d in record["interacts_with"]],
                    "severity": record["severity"],
                    "explanation": record["explanation"],
                },
            )
        )
    return documents


def main() -> None:
    settings = get_settings()
    settings.validate_for_ingestion()

    documents = _build_documents(SEED_INTERACTIONS)
    ids = [record["id"] for record in SEED_INTERACTIONS]

    vector_store = build_vector_store(settings)
    vector_store.add_documents(documents=documents, ids=ids)

    logger.info("ingestion_complete", extra={"extra_fields": {"count": len(documents)}})
    print(f"Upserted {len(documents)} drug-interaction records into '{settings.index_name}'.")


if __name__ == "__main__":
    main()
