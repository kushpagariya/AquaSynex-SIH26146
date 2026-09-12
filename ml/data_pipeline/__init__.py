"""
AquaSynex — Data Pipeline Package (Phase 2.2)
AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Modules:
- ingestion: Reads raw/synthetic datasets and quarantines generator metadata.
- validation: Validates data types, ranges, schema integrity, and UTXO conservation.
- cleaning: Deduplicates, canonicalizes identifiers, handles missing values.
- normalization: Standardizes timestamps, satoshi/BTC conversions, and relational structures.
"""

from .ingestion import DataIngestionEngine
from .validation import DataValidationEngine, ValidationResult
from .cleaning import DataCleaningEngine
from .normalization import DataNormalizationEngine

__all__ = [
    "DataIngestionEngine",
    "DataValidationEngine",
    "ValidationResult",
    "DataCleaningEngine",
    "DataNormalizationEngine"
]
