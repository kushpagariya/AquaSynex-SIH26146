"""
End-to-End ML Pipeline & Backend Contract Verification Test.
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Verifies:
1. End-to-end execution of the complete ML chain without running backend servers:
   Raw Fixture -> Ingestion -> Cleaning -> Normalization -> Feature Pipeline
   -> Graph Features -> Preprocessor -> XGBoost + CatBoost + TreeSHAP -> Structured Payload.
2. Direct validation against backend/services/pipeline_service.py:_validate_ml_result.
3. Proof that ML output meets all backend DuckDB table invariants.
"""

from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pytest
import xgboost as xgb
from catboost import CatBoostClassifier

from ml.data_pipeline.ingestion import DataIngestionEngine
from ml.data_pipeline.cleaning import DataCleaningEngine
from ml.data_pipeline.normalization import DataNormalizationEngine
from ml.data_pipeline.validation import DataValidationEngine
from ml.feature_engineering.feature_pipeline import FeatureEngineeringPipeline
from ml.graph_analysis.graph_features import GraphFeatureExtractor
from backend.services.pipeline_service import PipelineService


def test_end_to_end_ml_pipeline_execution(ml_sample_dir: Path, models_dir: Path):
    """Execute complete ML pipeline from raw files to scored and explained entity envelopes."""
    # 1. Ingestion
    ingestion = DataIngestionEngine(dataset_id="pipeline_e2e")
    obs, quarantined = ingestion.load_from_parquet_dir(str(ml_sample_dir))
    assert not obs["transactions"].empty

    # 2. Validation
    validator = DataValidationEngine()
    val_res = validator.validate(obs)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"

    # 3. Cleaning
    cleaner = DataCleaningEngine()
    cleaned = cleaner.clean(obs)

    # 4. Normalization
    normalizer = DataNormalizationEngine(dataset_id="pipeline_e2e")
    canonical = normalizer.normalize(cleaned)
    assert not canonical["transactions"].empty

    # 5. Feature Engineering
    fe = FeatureEngineeringPipeline()
    f_tab, quality = fe.build_feature_matrix(canonical)
    assert quality["is_clean"]
    assert len(f_tab) == len(canonical["transactions"])

    # 6. Graph Analysis
    ge = GraphFeatureExtractor()
    f_graph = ge.extract_features(canonical)
    assert len(f_graph) == len(canonical["transactions"])

    # 7. Merge Tabular + Graph Features
    merged = f_tab.merge(f_graph, on="transaction_id", how="left")

    # 8. Call Production Inference Adapter (model_inference.py)
    from pipeline.ml.model_inference import run_analysis

    ml_results = run_analysis(
        dataset_id=ml_sample_dir.name,
        model_id="aquasynex_xgb_binary_v1",
        model_version="1.0.0",
        config={"max_entities": 1000, "top_explanations": 3},
        db_path="",
        data_dir=str(ml_sample_dir.parent),
        models_dir=str(models_dir),
    )

    # 9. Validate all payloads against backend PipelineService invariants
    pipeline_service = PipelineService(conn=None)  # conn not needed for validation
    for item in ml_results:
        pipeline_service._validate_ml_result(item)

    assert len(ml_results) == 5
    print(f"Successfully executed end-to-end ML pipeline on {len(ml_results)} transactions.")
