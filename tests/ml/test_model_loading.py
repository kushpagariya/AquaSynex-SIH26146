"""
ML Artifact Loading & Integrity Audit Tests.
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Verifies:
1. Exact SHA256 checksum verification against models/model_metadata.json.
2. Deserialization of models/preprocessor_v1.joblib and verification of components.
3. Deserialization of models/aquasynex_xgb_binary_v1.json into native xgboost.Booster.
4. Deserialization of models/aquasynex_catboost_multiclass_v1.cbm into CatBoostClassifier.
5. Invariant checking: 46 canonical features, 71 post-transform dimensions, 11 multiclass classes.
"""

import hashlib
import json
from pathlib import Path
import pytest
import joblib
import xgboost as xgb
from catboost import CatBoostClassifier


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def test_model_metadata_structure(models_dir: Path):
    """Verify model_metadata.json exists, is valid JSON, and adheres to expected schema."""
    meta_path = models_dir / "model_metadata.json"
    assert meta_path.exists(), f"Metadata not found at {meta_path}"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model_version"] == "1.0.0"
    assert meta["release_tag"] == "Phase2.7-Production-Freeze"
    assert "artifacts" in meta
    assert "features" in meta
    assert "operating_points" in meta

    assert meta["features"]["canonical_input_count"] == 46
    assert meta["features"]["numeric_count"] == 44
    assert meta["features"]["categorical_count"] == 2
    assert meta["features"]["post_transform_dimension"] == 71


def test_artifact_sha256_checksums_match_metadata(models_dir: Path):
    """Verify that sha256 checksums of stored artifacts match model_metadata.json."""
    meta_path = models_dir / "model_metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    artifacts = meta["artifacts"]

    # 1. XGBoost binary model
    xgb_path = models_dir / "aquasynex_xgb_binary_v1.json"
    assert xgb_path.exists()
    assert compute_sha256(xgb_path) == artifacts["xgb_binary_model"]["sha256"]

    # 2. CatBoost multiclass model
    cat_path = models_dir / "aquasynex_catboost_multiclass_v1.cbm"
    assert cat_path.exists()
    assert compute_sha256(cat_path) == artifacts["catboost_multiclass_model"]["sha256"]

    # 3. Preprocessor bundle
    prep_path = models_dir / "preprocessor_v1.joblib"
    assert prep_path.exists()
    assert compute_sha256(prep_path) == artifacts["preprocessor"]["sha256"]


def test_preprocessor_loading_and_internal_contract(models_dir: Path):
    """Verify preprocessor_v1.joblib deserializes cleanly and provides all required scalers/encoders."""
    prep_path = models_dir / "preprocessor_v1.joblib"
    prep = joblib.load(prep_path)

    expected_keys = {
        "scaler",
        "ohe",
        "numeric_cols",
        "categorical_cols",
        "all_feature_names",
        "canonical_features",
        "target_classes_multiclass",
        "training_partition_rows",
    }
    for key in expected_keys:
        assert key in prep, f"Missing key '{key}' in preprocessor bundle"

    assert len(prep["canonical_features"]) == 46
    assert len(prep["numeric_cols"]) == 44
    assert len(prep["categorical_cols"]) == 2
    assert prep["categorical_cols"] == ["net_country", "net_asn"]
    assert len(prep["all_feature_names"]) == 71
    assert len(prep["target_classes_multiclass"]) == 11


def test_xgboost_booster_loading(models_dir: Path):
    """Verify aquasynex_xgb_binary_v1.json loads into native Booster with 71 input features."""
    xgb_path = models_dir / "aquasynex_xgb_binary_v1.json"
    booster = xgb.Booster()
    booster.load_model(str(xgb_path))

    assert booster.num_features() == 71


def test_catboost_classifier_loading(models_dir: Path):
    """Verify aquasynex_catboost_multiclass_v1.cbm loads into CatBoostClassifier with 11 classes."""
    cat_path = models_dir / "aquasynex_catboost_multiclass_v1.cbm"
    model = CatBoostClassifier()
    model.load_model(str(cat_path))

    assert len(model.classes_) == 11


def test_nonexistent_model_artifact_raises():
    """Verify attempting to load a missing model file raises FileNotFoundError or CatBoostError."""
    with pytest.raises(Exception):
        booster = xgb.Booster()
        booster.load_model("nonexistent_model_path.json")
