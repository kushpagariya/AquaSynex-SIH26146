"""Canonical error classes and definitions for AquaSynex Backend.

Authoritative reference: docs/backend/error-handling.md
"""

from typing import Any, Dict, Optional


class AppError(Exception):
    """Base exception for application errors mapped to canonical API error responses."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


# Validation Errors (4xx)
class ValidationError(AppError):
    def __init__(self, message: str = "Request validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__("VALIDATION_ERROR", message, 400, details)


class InvalidPaginationError(AppError):
    def __init__(self, message: str = "Invalid pagination parameters", details: Optional[Dict[str, Any]] = None):
        super().__init__("INVALID_PAGINATION", message, 400, details)


class InvalidFilterValueError(AppError):
    def __init__(self, message: str = "Invalid filter value", details: Optional[Dict[str, Any]] = None):
        super().__init__("INVALID_FILTER_VALUE", message, 400, details)


class InvalidSortFieldError(AppError):
    def __init__(self, message: str = "Invalid sort field", details: Optional[Dict[str, Any]] = None):
        super().__init__("INVALID_SORT_FIELD", message, 400, details)


class UnsupportedFileFormatError(AppError):
    def __init__(self, message: str = "Uploaded file format is not supported", details: Optional[Dict[str, Any]] = None):
        super().__init__("UNSUPPORTED_FILE_FORMAT", message, 400, details)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "Uploaded file exceeds maximum allowed size", details: Optional[Dict[str, Any]] = None):
        super().__init__("FILE_TOO_LARGE", message, 413, details)


# Resource Errors (404)
class DatasetNotFoundError(AppError):
    def __init__(self, dataset_id: str):
        super().__init__("DATASET_NOT_FOUND", f"Dataset '{dataset_id}' not found", 404, {"datasetId": dataset_id})


class AnalysisNotFoundError(AppError):
    def __init__(self, analysis_id: str):
        super().__init__("ANALYSIS_NOT_FOUND", f"Analysis run '{analysis_id}' not found", 404, {"analysisId": analysis_id})


class TransactionNotFoundError(AppError):
    def __init__(self, transaction_id: str):
        super().__init__("TRANSACTION_NOT_FOUND", f"Transaction '{transaction_id}' not found", 404, {"transactionId": transaction_id})


class AddressNotFoundError(AppError):
    def __init__(self, address_id: str):
        super().__init__("ADDRESS_NOT_FOUND", f"Address '{address_id}' not found", 404, {"addressId": address_id})


class ModelNotFoundError(AppError):
    def __init__(self, model_id: str, version: Optional[str] = None):
        super().__init__(
            "MODEL_NOT_FOUND",
            f"ML model '{model_id}' (version: {version}) not found",
            404,
            {"modelId": model_id, "modelVersion": version},
        )


class ResultNotFoundError(AppError):
    def __init__(self, entity_id: str, analysis_id: str):
        super().__init__(
            "RESULT_NOT_FOUND",
            f"No ML result for entity '{entity_id}' in analysis '{analysis_id}'",
            404,
            {"entityId": entity_id, "analysisId": analysis_id},
        )


# Dataset / Pipeline Errors
class DatasetError(AppError):
    def __init__(self, message: str = "Dataset cannot be processed", details: Optional[Dict[str, Any]] = None):
        super().__init__("DATASET_ERROR", message, 400, details)


class DatasetProcessingError(AppError):
    def __init__(self, message: str = "Dataset is currently being processed", details: Optional[Dict[str, Any]] = None):
        super().__init__("DATASET_PROCESSING", message, 409, details)


class DatasetAnalysisRunningError(AppError):
    def __init__(self, message: str = "An analysis is already running on this dataset", details: Optional[Dict[str, Any]] = None):
        super().__init__("DATASET_ANALYSIS_RUNNING", message, 409, details)


class PipelineError(AppError):
    def __init__(self, message: str = "Data ingestion or normalization pipeline failed", details: Optional[Dict[str, Any]] = None):
        super().__init__("PIPELINE_ERROR", message, 500, details)


# ML Errors
class MLError(AppError):
    def __init__(self, message: str = "ML pipeline failed unexpectedly", details: Optional[Dict[str, Any]] = None):
        super().__init__("ML_ERROR", message, 500, details)


class InvalidFeaturesError(AppError):
    def __init__(self, message: str = "Feature matrix missing required features", details: Optional[Dict[str, Any]] = None):
        super().__init__("INVALID_FEATURES", message, 500, details)


class ModelLoadError(AppError):
    def __init__(self, message: str = "Failed to load ML model artifact", details: Optional[Dict[str, Any]] = None):
        super().__init__("MODEL_LOAD_ERROR", message, 503, details)


class FeatureSchemaMismatchError(AppError):
    def __init__(self, message: str = "Feature schema version mismatch", details: Optional[Dict[str, Any]] = None):
        super().__init__("FEATURE_SCHEMA_MISMATCH", message, 500, details)


# Graph Errors
class GraphError(AppError):
    def __init__(self, message: str = "Graph construction or analysis failed", details: Optional[Dict[str, Any]] = None):
        super().__init__("GRAPH_ERROR", message, 500, details)


class GraphNotAvailableError(AppError):
    def __init__(self, message: str = "Graph has not been built for this analysis", details: Optional[Dict[str, Any]] = None):
        super().__init__("GRAPH_NOT_AVAILABLE", message, 404, details)


class GraphTooLargeError(AppError):
    def __init__(self, message: str = "Requested subgraph exceeds maximum allowed size", details: Optional[Dict[str, Any]] = None):
        super().__init__("GRAPH_TOO_LARGE", message, 400, details)


# Database Errors
class DatabaseError(AppError):
    def __init__(self, message: str = "Database query failed unexpectedly", details: Optional[Dict[str, Any]] = None):
        super().__init__("DATABASE_ERROR", message, 503, details)


class DatabaseUnavailableError(AppError):
    def __init__(self, message: str = "Database is unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__("DATABASE_UNAVAILABLE", message, 503, details)
