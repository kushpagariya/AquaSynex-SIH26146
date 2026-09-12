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

    # 8. Preprocessing
    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    X_num = prep["scaler"].transform(merged[prep["numeric_cols"]])
    X_cat = prep["ohe"].transform(merged[prep["categorical_cols"]])
    X_transformed = np.hstack([X_num, X_cat])

    # 9. Model Inferences
    # Binary detector (XGBoost)
    booster = xgb.Booster()
    booster.load_model(str(models_dir / "aquasynex_xgb_binary_v1.json"))
    dmat = xgb.DMatrix(X_transformed, feature_names=prep["all_feature_names"])
    risk_probs = booster.predict(dmat)

    # SHAP explanations
    contribs = booster.predict(dmat, pred_contribs=True)
    shaps = contribs[:, :-1]

    # Multiclass typology attribution (CatBoost)
    cat = CatBoostClassifier()
    cat.load_model(str(models_dir / "aquasynex_catboost_multiclass_v1.cbm"))
    multi_probs = cat.predict_proba(X_transformed)
    multi_preds = np.argmax(multi_probs, axis=1)
    classes = prep["target_classes_multiclass"]

    # 10. Construct Backend MLResult payloads
    now_iso = datetime.now(timezone.utc).isoformat()
    ml_results = []

    for i in range(len(merged)):
        txid = merged["transaction_id"].iloc[i]
        r_prob = float(risk_probs[i])

        # Assign risk level based on frozen thresholds
        if r_prob >= 0.67:
            risk_level = "critical"
        elif r_prob >= 0.50:
            risk_level = "high"
        elif r_prob >= 0.32:
            risk_level = "medium"
        else:
            risk_level = "low"

        pred_label = classes[multi_preds[i]]
        confidence = float(multi_probs[i, multi_preds[i]])

        # Top 3 feature explanations
        row_shap = shaps[i]
        top_indices = np.argsort(np.abs(row_shap))[::-1][:3]
        explanations = [
            {
                "feature": prep["all_feature_names"][idx],
                "attribution": float(row_shap[idx]),
                "value": float(X_transformed[i, idx]),
            }
            for idx in top_indices
        ]

        result_payload = {
            "entity_id": txid,
            "entity_type": "transaction",
            "anomaly_score": r_prob,
            "risk_score": r_prob,
            "risk_level": risk_level,
            "confidence": confidence,
            "prediction_label": pred_label,
            "explanations": explanations,
            "features": [{"name": k, "value": float(v) if isinstance(v, (int, float, np.number)) else str(v)} for k, v in merged.iloc[i].to_dict().items()],
            "graph_evidence": [{"cluster_size": int(merged["hist_cluster_size"].iloc[i])}],
            "predicted_at": now_iso,
        }
        ml_results.append(result_payload)

    # 11. Validate all payloads against backend PipelineService invariants
    pipeline_service = PipelineService(conn=None)  # conn not needed for validation
    for item in ml_results:
        pipeline_service._validate_ml_result(item)

    assert len(ml_results) == 5
    print(f"Successfully executed end-to-end ML pipeline on {len(ml_results)} transactions.")
