from app.core.config import Settings
from app.services.pinecone_service import PineconeService


class _FakeDoc:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


class _FakeNamespaceStore:
    def __init__(self, results):
        self._results = results
        self.last_query = None
        self.last_k = None
        self.last_filter = None

    def similarity_search_with_score(self, query, k=5, filter=None):
        self.last_query = query
        self.last_k = k
        self.last_filter = filter
        return self._results


def test_query_namespace_returns_plain_dicts():
    settings = Settings(openrouter_api_key="key", pinecone_api_key="key")
    fake_store = _FakeNamespaceStore(
        results=[(_FakeDoc("ACE inhibitors are first-line for hypertension.", {"section": "JNC-8"}), 0.87)]
    )
    service = PineconeService(settings=settings, namespace_stores={"clinical-guidelines": fake_store})

    results = service.query_namespace("hypertension treatment", namespace="clinical-guidelines")

    assert len(results) == 1
    assert results[0]["content"] == "ACE inhibitors are first-line for hypertension."
    assert results[0]["metadata"] == {"section": "JNC-8"}
    assert results[0]["score"] == 0.87


def test_query_namespace_isolated_from_other_namespaces():
    settings = Settings(openrouter_api_key="key", pinecone_api_key="key")
    guideline_store = _FakeNamespaceStore(results=[(_FakeDoc("guideline text", {}), 0.9)])
    contraindication_store = _FakeNamespaceStore(results=[(_FakeDoc("contraindication text", {}), 0.8)])
    service = PineconeService(
        settings=settings,
        namespace_stores={
            "clinical-guidelines": guideline_store,
            "contraindications": contraindication_store,
        },
    )

    guideline_results = service.query_namespace("query", namespace="clinical-guidelines")
    contraindication_results = service.query_namespace("query", namespace="contraindications")

    assert guideline_results[0]["content"] == "guideline text"
    assert contraindication_results[0]["content"] == "contraindication text"


def test_query_namespace_passes_filter_and_top_k_through():
    settings = Settings(openrouter_api_key="key", pinecone_api_key="key")
    fake_store = _FakeNamespaceStore(results=[])
    service = PineconeService(settings=settings, namespace_stores={"contraindications": fake_store})

    service.query_namespace("aspirin", namespace="contraindications", top_k=3, filter={"drug": "aspirin"})

    assert fake_store.last_query == "aspirin"
    assert fake_store.last_k == 3
    assert fake_store.last_filter == {"drug": "aspirin"}
