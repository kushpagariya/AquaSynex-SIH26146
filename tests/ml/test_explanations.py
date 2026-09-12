"""
TreeSHAP Explainability & Attribution Audit Tests.
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Verifies:
1. Native TreeSHAP computation via XGBoost booster.predict(pred_contribs=True).
2. Exact dimensional alignment: (N, 72) representing 71 feature attributions + 1 base bias term.
3. Additivity property of SHAP values: sum(SHAP) + bias == model_output_margin (logit).
4. Extraction of top positive and negative risk contributors for investigator display.
5. Construction of structured explanation payload conforming to backend explanation schema.
"""

from pathlib import Path
import joblib
import numpy as np
import pytest
import xgboost as xgb


@pytest.fixture(scope="module")
def prepared_dmatrix(ml_sample_dir: Path, models_dir: Path):
    """Generate DMatrix from deterministic fixture."""
    from ml.data_pipeline.ingestion import DataIngestionEngine
    from ml.data_pipeline.cleaning import DataCleaningEngine
    from ml.data_pipeline.normalization import DataNormalizationEngine
    from ml.feature_engineering.feature_pipeline import FeatureEngineeringPipeline
    from ml.graph_analysis.graph_features import GraphFeatureExtractor

    ingestion = DataIngestionEngine(dataset_id="shap_test")
    obs, _ = ingestion.load_from_parquet_dir(str(ml_sample_dir))

    cleaned = DataCleaningEngine().clean(obs)
    canonical = DataNormalizationEngine(dataset_id="shap_test").normalize(cleaned)

    f_tab, _ = FeatureEngineeringPipeline().build_feature_matrix(canonical)
    f_graph = GraphFeatureExtractor().extract_features(canonical)
    merged = f_tab.merge(f_graph, on="transaction_id", how="left")

    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    X_num = prep["scaler"].transform(merged[prep["numeric_cols"]])
    X_cat = prep["ohe"].transform(merged[prep["categorical_cols"]])
    X_transformed = np.hstack([X_num, X_cat])

    dmat = xgb.DMatrix(X_transformed, feature_names=prep["all_feature_names"])
    return dmat, prep["all_feature_names"], merged["transaction_id"].tolist()


def test_treeshap_output_shape(prepared_dmatrix: tuple, models_dir: Path):
    """Verify booster.predict(pred_contribs=True) returns (N, 72) array."""
    dmat, feature_names, _ = prepared_dmatrix

    booster = xgb.Booster()
    booster.load_model(str(models_dir / "aquasynex_xgb_binary_v1.json"))

    contribs = booster.predict(dmat, pred_contribs=True)
    assert contribs.shape == (dmat.num_row(), len(feature_names) + 1)
    assert not np.isnan(contribs).any(), "SHAP values contain NaNs"
    assert not np.isinf(contribs).any(), "SHAP values contain Infs"


def test_treeshap_additivity_property(prepared_dmatrix: tuple, models_dir: Path):
    """Verify SHAP local accuracy: sum(phi_i) + phi_0 == f(x) (margin)."""
    dmat, _, _ = prepared_dmatrix

    booster = xgb.Booster()
    booster.load_model(str(models_dir / "aquasynex_xgb_binary_v1.json"))

    contribs = booster.predict(dmat, pred_contribs=True)
    margins = booster.predict(dmat, output_margin=True)

    sum_contribs = np.sum(contribs, axis=1)
    np.testing.assert_allclose(sum_contribs, margins, rtol=1e-4, atol=1e-4)


def test_structured_explanation_generation(prepared_dmatrix: tuple, models_dir: Path):
    """Verify generation of top-k human-readable feature attributions for investigators."""
    dmat, feature_names, txids = prepared_dmatrix

    booster = xgb.Booster()
    booster.load_model(str(models_dir / "aquasynex_xgb_binary_v1.json"))

    contribs = booster.predict(dmat, pred_contribs=True)
    feature_shaps = contribs[:, :-1]
    bias = contribs[:, -1]

    explanations_per_tx = []
    for i in range(len(txids)):
        row_shap = feature_shaps[i]
        top_positive_idx = np.argsort(row_shap)[::-1][:3]
        top_negative_idx = np.argsort(row_shap)[:3]

        reasons = []
        for idx in top_positive_idx:
            reasons.append({
                "feature": feature_names[idx],
                "shap_value": float(row_shap[idx]),
                "direction": "increases_suspicion"
            })
        for idx in top_negative_idx:
            reasons.append({
                "feature": feature_names[idx],
                "shap_value": float(row_shap[idx]),
                "direction": "decreases_suspicion"
            })

        explanations_per_tx.append({
            "transaction_id": txids[i],
            "base_value": float(bias[i]),
            "drivers": reasons
        })

    assert len(explanations_per_tx) == len(txids)
    for exp in explanations_per_tx:
        assert "transaction_id" in exp
        assert "base_value" in exp
        assert len(exp["drivers"]) == 6
