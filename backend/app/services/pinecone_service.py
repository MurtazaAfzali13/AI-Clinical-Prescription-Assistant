"""Vector store wrapper for the drug-interaction knowledge base.

Uses langchain-pinecone + OpenRouter's OpenAI-compatible embeddings
endpoint. Isolated behind a small interface so it can be mocked in tests
without real network access or credentials.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.core.config import Settings
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DrugKnowledgeMatch:
    drug_name: str
    interacts_with: list[str]
    severity: str
    explanation: str
    score: float


def get_embeddings(settings: Settings) -> OpenAIEmbeddings:
    """OpenRouter exposes an OpenAI-compatible API for embeddings."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        check_embedding_ctx_length=False,
    )


class PineconeService:
    """Query interface over the drug-interaction vector index."""

    def __init__(self, settings: Settings, vector_store: PineconeVectorStore | None = None) -> None:
        self._settings = settings
        self._vector_store = vector_store

    def _ensure_store(self) -> PineconeVectorStore:
        if self._vector_store is not None:
            return self._vector_store
        try:
            self._vector_store = PineconeVectorStore(
                index_name=self._settings.index_name,
                embedding=get_embeddings(self._settings),
                pinecone_api_key=self._settings.pinecone_api_key,
            )
            return self._vector_store
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Could not connect to Pinecone: {exc}") from exc

    def find_interactions(self, medication_name: str, top_k: int = 5) -> list[DrugKnowledgeMatch]:
        """Return the closest known interaction records for a medication."""
        try:
            store = self._ensure_store()
            results = store.similarity_search_with_score(medication_name, k=top_k)
        except VectorStoreError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Pinecone query failed: {exc}") from exc

        matches: list[DrugKnowledgeMatch] = []
        for doc, score in results:
            meta = doc.metadata or {}
            matches.append(
                DrugKnowledgeMatch(
                    drug_name=meta.get("drug_name", medication_name),
                    interacts_with=meta.get("interacts_with", []),
                    severity=meta.get("severity", "low"),
                    explanation=meta.get("explanation", doc.page_content),
                    score=score,
                )
            )
        return matches