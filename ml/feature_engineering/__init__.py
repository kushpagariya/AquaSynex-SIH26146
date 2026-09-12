"""
AquaSynex — Feature Engineering Package (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Modules:
- transaction_features: Transaction-level counts, amounts, rates, and log transforms.
- address_features: Historical address behavior with strict t < T_tx anti-leakage logic.
- temporal_features: Time-of-day, inter-transaction deltas, and rolling window velocities.
- network_features: Network transport ports, ASN, and address IP diversity.
- feature_pipeline: Master orchestrator, quality checks, and export engine.
"""

from .transaction_features import TransactionFeatureExtractor
from .address_features import AddressFeatureExtractor
from .temporal_features import TemporalFeatureExtractor
from .network_features import NetworkFeatureExtractor
from .feature_pipeline import FeatureEngineeringPipeline, run_feature_pipeline

__all__ = [
    "TransactionFeatureExtractor",
    "AddressFeatureExtractor",
    "TemporalFeatureExtractor",
    "NetworkFeatureExtractor",
    "FeatureEngineeringPipeline",
    "run_feature_pipeline"
]
