"""ML Result schemas matching docs/ml/model-output-contract.md and docs/backend/request-response-schemas.md."""

from datetime import datetime
from typing import Any, List, Optional, Union
from backend.schemas.common import CamelModel


class FeatureExplanationSchema(CamelModel):
    feature_name: str
    display_label: str
    shap_value: float
    direction: str  # 'increases_risk' | 'decreases_risk' | 'neutral'
    importance_rank: int
    normalized_importance: float
    feature_value: Optional[Union[float, int, str]] = None
    feature_unit: Optional[str] = None


class FeatureValueSchema(CamelModel):
    feature_name: str
    raw_value: Optional[Union[float, int, str]] = None
    normalized_value: Optional[float] = None
    is_imputed: bool = False
    imputation_method: Optional[str] = None


class GraphEvidenceSchema(CamelModel):
    evidence_type: str
    label: str
    feature_name: str
    value: Union[float, int]
    description: str


class PredictionSchema(CamelModel):
    anomaly_score: float
    risk_score: float
    risk_level: str
    prediction_label: Optional[str] = None
    confidence: Optional[float] = None


class ModelMetadataSchema(CamelModel):
    model_id: str
    model_version: str
    feature_schema_version: str = "1.0.0"
    model_type: str = "anomaly_detection"
    algorithm: str = "IsolationForest"


class MLResultSummary(CamelModel):
    entity_id: str
    entity_type: str
    anomaly_score: float
    risk_score: float
    risk_level: str
    prediction_label: Optional[str] = None
    model_id: str
    model_version: str
    predicted_at: datetime


class MLResultDetail(MLResultSummary):
    confidence: Optional[float] = None
    explanations: List[FeatureExplanationSchema] = []
    features: List[FeatureValueSchema] = []
    graph_evidence: List[GraphEvidenceSchema] = []
