"""
Feature -> Preprocessor -> Model Compatibility Audit Tests.
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Verifies:
1. Feature pipeline output schema aligns 100% with preprocessor canonical features.
2. RobustScaler correctly transforms 44 numeric features without NaN/Inf generation.
3. OneHotEncoder correctly transforms 2 categorical features (net_country, net_asn).
4. Unseen categorical values evaluate to all-zero vectors without crashing (handle_unknown='ignore').
5. Post-transform dimension matches exactly 71 columns and expected model feature names.
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from ml.data_pipeline.ingestion import DataIngestionEngine
from ml.data_pipeline.cleaning import DataCleaningEngine
from ml.data_pipeline.normalization import DataNormalizationEngine
from ml.feature_engineering.feature_pipeline import FeatureEngineeringPipeline
from ml.graph_analysis.graph_features import GraphFeatureExtractor


@pytest.fixture(scope="module")
def prepared_features(ml_sample_dir: Path):
    """Run data pipeline, feature engineering, and graph features on deterministic fixture."""
    ingestion = DataIngestionEngine(dataset_id="compat_test")
    obs, _ = ingestion.load_from_parquet_dir(str(ml_sample_dir))

    cleaner = DataCleaningEngine()
    cleaned = cleaner.clean(obs)

    normalizer = DataNormalizationEngine(dataset_id="compat_test")
    canonical = normalizer.normalize(cleaned)

    fe_pipeline = FeatureEngineeringPipeline()
    feat_matrix, _ = fe_pipeline.build_feature_matrix(canonical)

    graph_extractor = GraphFeatureExtractor()
    graph_matrix = graph_extractor.extract_features(canonical)

    merged = feat_matrix.merge(graph_matrix, on="transaction_id", how="left")
    return merged


def test_feature_pipeline_covers_all_46_canonical_features(prepared_features: pd.DataFrame, models_dir: Path):
    """Verify that every canonical feature required by preprocessor_v1.joblib is produced."""
    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    expected_canonical = prep["canonical_features"]

    missing = [c for c in expected_canonical if c not in prepared_features.columns]
    assert len(missing) == 0, f"Feature pipeline is missing canonical features: {missing}"


def test_preprocessor_transformation_pipeline(prepared_features: pd.DataFrame, models_dir: Path):
    """Verify RobustScaler and OneHotEncoder transform pipeline features into valid 71-dim matrix."""
    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    scaler = prep["scaler"]
    ohe = prep["ohe"]
    numeric_cols = prep["numeric_cols"]
    categorical_cols = prep["categorical_cols"]
    all_feature_names = prep["all_feature_names"]

    # 1. Numeric transformation
    X_num = scaler.transform(prepared_features[numeric_cols])
    assert X_num.shape == (len(prepared_features), 44)
    assert not np.isnan(X_num).any(), "Numeric transform produced unexpected NaNs"
    assert not np.isinf(X_num).any(), "Numeric transform produced unexpected Infs"

    # 2. Categorical transformation
    X_cat = ohe.transform(prepared_features[categorical_cols])
    assert X_cat.shape == (len(prepared_features), 27)
    assert not np.isnan(X_cat).any(), "Categorical transform produced unexpected NaNs"

    # 3. Concatenation
    X_transformed = np.hstack([X_num, X_cat])
    assert X_transformed.shape == (len(prepared_features), 71)
    assert X_transformed.shape[1] == len(all_feature_names)


def test_unseen_categories_evaluated_to_zero_vector(prepared_features: pd.DataFrame, models_dir: Path):
    """Verify that unseen country codes and ASNs evaluate to zero without raising exceptions."""
    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    ohe = prep["ohe"]

    unseen_df = pd.DataFrame({
        "net_country": ["ZZ", "QQ"],
        "net_asn": [999999, 888888]
    })
    X_cat_unseen = ohe.transform(unseen_df)
    assert X_cat_unseen.shape == (2, 27)
    # Because categories are unseen and handle_unknown='ignore', all entries should be 0.0
    assert (X_cat_unseen == 0.0).all()


def test_missing_numeric_column_raises_keyerror(prepared_features: pd.DataFrame, models_dir: Path):
    """Verify that dropping a required numeric feature fails deterministically at transform time."""
    prep = joblib.load(models_dir / "preprocessor_v1.joblib")
    scaler = prep["scaler"]
    numeric_cols = prep["numeric_cols"]

    incomplete_df = prepared_features.drop(columns=[numeric_cols[0]])
    with pytest.raises(KeyError):
        scaler.transform(incomplete_df[numeric_cols])
