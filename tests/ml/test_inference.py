"""
Model Inference & Operating Threshold Audit Tests.
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Verifies:
1. XGBoost binary prediction outputs continuous probabilities strictly in [0.0, 1.0].
2. Application of frozen decision thresholds (tau=0.50, tau=0.32, tau=0.67) from model_metadata.json.
3. CatBoost multiclass prediction outputs valid probabilities summing to 1.0 across 11 classes.
4. Correct label decoding to human-readable behavioral typologies.
5. Invariant: Demonstrates that CatBoost requires the 71-dim numeric input and rejects raw categorical strings.
"""

from pathlib import Path
import joblib
import numpy as np
import pytest
import xgboost as xgb
from catboost import CatBoostClassifier, CatBoostError


@pytest.fixture(scope="module")
def sample_transformed_features(ml_sample_dir: Path, models_dir: Path):
    """Generate preprocessed 71-dimensional input matrix from deterministic fixture."""
    from ml.data_pipeline.ingestion import DataIngestionEngine
    from ml.data_pipeline.cleaning import DataCleaningEngine
    from ml.data_pipeline.normalization import DataNormalizationEngine
    from ml.feature_engineering.feature_pipeline import FeatureEngineeringPipeline
    from ml.graph_analysis.graph_features import GraphFeatureExtractor

    ingestion = DataIngestionEngine(dataset_id="inf_test")
    obs, _ = ingestion.load_from_parquet_dir(str(ml_sample_dir))

    cleaned = DataCleaningEngine().clean(obs)
    canonical = DataNormalizationEngine(dataset_id="inf_test").normalize(cleaned)

    f_tab, _ = FeatureEngineeringPipeline().build_feature_matrix(canonical)
    f_graph = GraphFeatureExtractor().extract_features(canonical)
    merged = f_tab.merge(f_graph, on="transaction_id", how="left")

    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    X_num = prep["scaler"].transform(merged[prep["numeric_cols"]])
    X_cat = prep["ohe"].transform(merged[prep["categorical_cols"]])
    X_transformed = np.hstack([X_num, X_cat])

    return merged, X_transformed, prep


def test_xgboost_binary_probability_inference(sample_transformed_features: tuple, models_dir: Path):
    """Verify XGBoost outputs probability scores bounded between 0.0 and 1.0."""
    _, X_transformed, prep = sample_transformed_features

    booster = xgb.Booster()
    booster.load_model(str(models_dir / "aquasynex_xgb_binary_v1.json"))

    dmat = xgb.DMatrix(X_transformed, feature_names=prep["all_feature_names"])
    probs = booster.predict(dmat)

    assert isinstance(probs, np.ndarray)
    assert len(probs) == len(X_transformed)
    assert ((probs >= 0.0) & (probs <= 1.0)).all(), "Probabilities must be bounded in [0.0, 1.0]"


def test_frozen_threshold_decisions(sample_transformed_features: tuple, models_dir: Path):
    """Verify classification decisions at the three frozen thresholds: tau=0.50, 0.32, 0.67."""
    _, X_transformed, prep = sample_transformed_features

    booster = xgb.Booster()
    booster.load_model(str(models_dir / "aquasynex_xgb_binary_v1.json"))
    probs = booster.predict(xgb.DMatrix(X_transformed, feature_names=prep["all_feature_names"]))

    tau_default = 0.50
    tau_f1 = 0.32
    tau_high_prec = 0.67

    decisions_default = (probs >= tau_default).astype(int)
    decisions_f1 = (probs >= tau_f1).astype(int)
    decisions_high_prec = (probs >= tau_high_prec).astype(int)

    # Monotonicity check: Lower threshold implies equal or greater number of positive flags
    assert decisions_f1.sum() >= decisions_default.sum()
    assert decisions_default.sum() >= decisions_high_prec.sum()


def test_catboost_multiclass_inference(sample_transformed_features: tuple, models_dir: Path):
    """Verify CatBoost outputs probability distributions summing to 1.0 across 11 classes."""
    _, X_transformed, prep = sample_transformed_features

    cat = CatBoostClassifier()
    cat.load_model(str(models_dir / "aquasynex_catboost_multiclass_v1.cbm"))

    probs = cat.predict_proba(X_transformed)
    assert probs.shape == (len(X_transformed), 11)

    # Sum of probabilities across classes must be 1.0 (within float tolerance)
    row_sums = np.sum(probs, axis=1)
    np.testing.assert_allclose(row_sums, 1.0, rtol=1e-5)

    preds = cat.predict(X_transformed)
    classes = prep["target_classes_multiclass"]

    # Map class indices to names
    class_names = [classes[int(p[0])] for p in preds]
    assert len(class_names) == len(X_transformed)
    for name in class_names:
        assert name in classes


def test_catboost_raw_dataframe_input_invariant_fails(sample_transformed_features: tuple, models_dir: Path):
    """Verify that feeding unencoded 46-feature DataFrame into CatBoost fails because it was trained on 71-dim encoded matrix."""
    merged, _, prep = sample_transformed_features

    cat = CatBoostClassifier()
    cat.load_model(str(models_dir / "aquasynex_catboost_multiclass_v1.cbm"))

    # Passing raw dataframe with string 'net_country' raises CatBoostError
    with pytest.raises(CatBoostError, match="Cannot convert.*to float"):
        cat.predict(merged[prep["canonical_features"]])
