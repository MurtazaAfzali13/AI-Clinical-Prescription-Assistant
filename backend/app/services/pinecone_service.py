"""Vector store wrapper for the drug-interaction knowledge base.

Uses langchain-pinecone + OpenRouter's OpenAI-compatible embeddings
endpoint. We build the Pinecone `Index` object ourselves (via the raw
`pinecone` client, using the API key from our own Settings) instead of
letting `PineconeVectorStore` resolve the key -- langchain-pinecone's
`from_texts`/`from_documents`/index_name-only construction path only reads
`PINECONE_API_KEY` from `os.environ`, which pydantic-settings does NOT
populate just because it's in `.env`. Passing a ready `Index` object sidesteps
that entirely.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone as PineconeClient

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


def build_vector_store(settings: Settings, namespace: str | None = None) -> PineconeVectorStore:
    """Builds a PineconeVectorStore from an explicitly-constructed Index,
    so the Pinecone API key always comes from our own Settings -- never
    from an ambient environment variable. `namespace=None` uses Pinecone's
    default namespace (where the drug-interaction seed data lives)."""
    client = PineconeClient(api_key=settings.pinecone_api_key)
    index = client.Index(settings.index_name)
    return PineconeVectorStore(index=index, embedding=get_embeddings(settings), namespace=namespace)


class PineconeService:
    """Query interface over the Pinecone index. `find_interactions` keeps
    using the default namespace (drug-drug interactions, unchanged from
    before namespaces existed); `query_namespace` gives the CDSS
    specialist agents (Contraindication, Guideline, Alternative Therapy)
    access to their own isolated namespaces, so a semantically-similar
    contraindication record can never leak into a guideline lookup or
    vice versa."""

    def __init__(
        self,
        settings: Settings,
        vector_store: PineconeVectorStore | None = None,
        namespace_stores: dict[str, PineconeVectorStore] | None = None,
    ) -> None:
        self._settings = settings
        self._vector_store = vector_store
        self._namespace_stores: dict[str, PineconeVectorStore] = dict(namespace_stores or {})

    def _ensure_store(self) -> PineconeVectorStore:
        if self._vector_store is not None:
            return self._vector_store
        try:
            self._vector_store = build_vector_store(self._settings)
            return self._vector_store
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Could not connect to Pinecone: {exc}") from exc

    def _ensure_namespace_store(self, namespace: str) -> PineconeVectorStore:
        if namespace not in self._namespace_stores:
            try:
                self._namespace_stores[namespace] = build_vector_store(self._settings, namespace=namespace)
            except Exception as exc:  # noqa: BLE001
                raise VectorStoreError(f"Could not connect to Pinecone namespace '{namespace}': {exc}") from exc
        return self._namespace_stores[namespace]

    def find_interactions(self, medication_name: str, top_k: int = 5) -> list[DrugKnowledgeMatch]:
        """Return the closest known interaction records for a medication.

        Filters by the `drug_name_lower` metadata field so that Pinecone's
        semantic similarity search can't return a *different* drug's record
        just because its seed sentence reads similarly (e.g. "Ibuprofen" and
        "Acetaminophen" interaction sentences are worded almost identically).
        """
        try:
            store = self._ensure_store()
            results = store.similarity_search_with_score(
                medication_name,
                k=top_k,
                filter={"drug_name_lower": medication_name.strip().lower()},
            )
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

    def query_namespace(
        self, query_text: str, namespace: str, top_k: int = 5, filter: dict | None = None
    ) -> list[dict]:
        """Generic namespace-scoped semantic search, returning plain dicts
        (`content`, `metadata`, `score`) since different namespaces
        (contraindications, clinical-guidelines) have different metadata
        shapes -- unlike `find_interactions`, this isn't specific to the
        drug-interaction schema."""
        try:
            store = self._ensure_namespace_store(namespace)
            results = store.similarity_search_with_score(query_text, k=top_k, filter=filter)
        except VectorStoreError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Pinecone namespace '{namespace}' query failed: {exc}") from exc

        return [
            {"content": doc.page_content, "metadata": doc.metadata or {}, "score": score}
            for doc, score in results
        ]
