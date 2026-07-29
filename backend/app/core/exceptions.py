"""Custom exception hierarchy for the Doctor Copilot backend.

Every domain error inherits from `AppError` so the API layer can catch a
single base class and translate it into a consistent JSON error response.
"""


class AppError(Exception):
    """Base class for all application-level errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExtractionError(AppError):
    """Raised when the Extractor agent fails to parse doctor input into
    structured prescription data."""

    status_code = 422
    error_code = "extraction_failed"


class SafetyCheckError(AppError):
    """Raised when the Safety/RAG agent cannot complete an interaction check
    (e.g. vector store unreachable)."""

    status_code = 502
    error_code = "safety_check_failed"


class VectorStoreError(AppError):
    """Raised for Pinecone connectivity / query failures."""

    status_code = 502
    error_code = "vector_store_error"


class ValidationFailedError(AppError):
    """Raised when structured prescription data fails business validation."""

    status_code = 422
    error_code = "validation_failed"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
