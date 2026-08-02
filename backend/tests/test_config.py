import pytest

from app.core.config import Settings


def test_validate_for_ingestion_passes_when_configured():
    settings = Settings(openrouter_api_key="key", pinecone_api_key="key")
    settings.validate_for_ingestion()  # should not raise


def test_validate_for_ingestion_raises_when_missing_keys():
    settings = Settings(openrouter_api_key="", pinecone_api_key="")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        settings.validate_for_ingestion()
