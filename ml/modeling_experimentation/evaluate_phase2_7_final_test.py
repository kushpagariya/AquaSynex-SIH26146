"""
AquaSynex Phase 2.7: Final Test Evaluation & Production Model Freeze
===================================================================
Executes the one-shot evaluation of the frozen XGBoost binary detector
and CatBoost multiclass attribution model on the quarantined test set (N=1,500),
computes side-by-side validation vs test metrics, evaluates temporal generalization,
computes test SHAP drivers, and serializes production-grade model artifacts to models/.
"""

import os
import sys
import json
import time
import hashlib
import joblib
import yaml
import duckdb
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    log_loss,
    classification_report
)
import xgboost as xgb
from catboost import CatBoostClassifier

def sha256_checksum(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 80)
    print(" AquaSynex Phase 2.7: One-Shot Final Test Evaluation & Production Freeze")
    print("=" * 80)

    SEED = 42
    os.makedirs("models", exist_ok=True)

    # 1. Load Dataset & Manifest
    pq_path = "data/processed/modeling_v2/modeling_dataset.parquet"
    manifest_path = "data/processed/modeling_v2/feature_manifest.yaml"
    if not os.path.exists(pq_path):
        raise FileNotFoundError(f"Dataset not found at {pq_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    canonical_features = manifest["canonical_feature_names"]
    categorical_cols = ["net_country", "net_asn"]
    numeric_cols = [c for c in canonical_features if c not in categorical_cols]

    print(f"[*] Canonical Features: {len(canonical_features)} ({len(numeric_cols)} numeric + {len(categorical_cols)} categorical)")

    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{pq_path}')").df()
    con.close()

    df_train = df[df["temporal_split"] == "train"].copy()
    df_val = df[df["temporal_split"] == "val"].copy()
    df_test = df[df["temporal_split"] == "test"].copy()

    y_train = df_train["target_binary"].values
    y_val = df_val["target_binary"].values
    y_test = df_test["target_binary"].values

    y_train_multi = df_train["target_multiclass"].values
    y_val_multi = df_val["target_multiclass"].values
    y_test_multi = df_test["target_multiclass"].values

    print(f"[*] Train Partition: {len(df_train):,} rows | Suspicious: {y_train.mean():.2%}")
    print(f"[*] Val Partition:   {len(df_val):,} rows | Suspicious: {y_val.mean():.2%}")
    print(f"[*] Test Partition:  {len(df_test):,} rows | Suspicious: {y_test.mean():.2%} [UNBLINDING EXACTLY ONCE]")

    # 2. Preprocessing (Fit strictly on train)
    print("\n[*] Fitting preprocessing pipeline strictly on train partition...")
    scaler = RobustScaler()
    X_train_num = scaler.fit_transform(df_train[numeric_cols])
    X_val_num = scaler.transform(df_val[numeric_cols])
    X_test_num = scaler.transform(df_test[numeric_cols])

    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    X_train_cat = ohe.fit_transform(df_train[categorical_cols])
    X_val_cat = ohe.transform(df_val[categorical_cols])
    X_test_cat = ohe.transform(df_test[categorical_cols])

    cat_feature_names = list(ohe.get_feature_names_out(categorical_cols))
    all_feature_names = numeric_cols + cat_feature_names

    X_train = np.hstack([X_train_num, X_train_cat])
    X_val = np.hstack([X_val_num, X_val_cat])
    X_test = np.hstack([X_test_num, X_test_cat])

    print(f"[+] Transformed feature vector dimension: {X_train.shape[1]} columns")

    # 3. Fit Exact Frozen Binary XGBoost Model
    print("\n[*] Training exact frozen XGBoost binary detector on train partition...")
    scale_pos = float(len(y_train) - sum(y_train)) / sum(y_train)
    xgb_clf = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        random_state=SEED,
        n_jobs=-1
    )
    t0 = time.time()
    xgb_clf.fit(X_train, y_train)
    fit_time_xgb = time.time() - t0
    print(f"[+] XGBoost training complete in {fit_time_xgb:.2f}s")

    # 4. Fit Exact Frozen Multiclass CatBoost Model
    print("\n[*] Training exact frozen CatBoost 11-class attribution model on train partition...")
    classes = sorted(list(np.unique(y_train_multi)))
    class_to_idx = {c: i for i, c in enumerate(classes)}
    y_train_idx = np.array([class_to_idx[c] for c in y_train_multi])
    y_val_idx = np.array([class_to_idx[c] for c in y_val_multi])
    y_test_idx = np.array([class_to_idx[c] for c in y_test_multi])

    cat_multi = CatBoostClassifier(
        iterations=350,
        depth=6,
        learning_rate=0.06,
        loss_function="MultiClass",
        eval_metric="MultiClass",
        random_seed=SEED,
        verbose=0
    )
    t0_cat = time.time()
    cat_multi.fit(X_train, y_train_idx)
    fit_time_cat = time.time() - t0_cat
    print(f"[+] CatBoost multiclass training complete in {fit_time_cat:.2f}s")

    # 5. One-Shot Prediction Pass
    print("\n[*] Executing one-shot prediction pass on validation and test partitions...")
    t_inf_val = time.time()
    val_probs_binary = xgb_clf.predict_proba(X_val)[:, 1]
    lat_val = (time.time() - t_inf_val) / len(X_val) * 1000

    t_inf_test = time.time()
    test_probs_binary = xgb_clf.predict_proba(X_test)[:, 1]
    lat_test = (time.time() - t_inf_test) / len(X_test) * 1000

    val_probs_multi = cat_multi.predict_proba(X_val)
    val_preds_multi = np.argmax(val_probs_multi, axis=1)

    test_probs_multi = cat_multi.predict_proba(X_test)
    test_preds_multi = np.argmax(test_probs_multi, axis=1)

    # 6. Binary Evaluation at Frozen Operating Points
    frozen_thresholds = [
        ("Default Baseline (tau=0.50)", 0.50),
        ("F1-Optimal (tau=0.32)", 0.32),
        ("High-Precision R95 (tau=0.67)", 0.67)
    ]

    val_roc = roc_auc_score(y_val, val_probs_binary)
    val_pr = average_precision_score(y_val, val_probs_binary)
    test_roc = roc_auc_score(y_test, test_probs_binary)
    test_pr = average_precision_score(y_test, test_probs_binary)

    delta_roc = test_roc - val_roc
    delta_pr = test_pr - val_pr

    print("\n" + "=" * 80)
    print(" BINARY DISCRIMINATION SUMMARY (VALIDATION vs TEST)")
    print("=" * 80)
    print(f"Metric       Validation (N=1,500)   Test (N=1,500)   Delta (Test - Val)")
    print(f"ROC-AUC      {val_roc:18.4f}   {test_roc:14.4f}   {delta_roc:+18.4f}")
    print(f"PR-AUC       {val_pr:18.4f}   {test_pr:14.4f}   {delta_pr:+18.4f}")

    thresh_results = []
    for label, tau in frozen_thresholds:
        p_val = (val_probs_binary >= tau).astype(int)
        p_test = (test_probs_binary >= tau).astype(int)

        rec_val = recall_score(y_val, p_val, zero_division=0)
        rec_test = recall_score(y_test, p_test, zero_division=0)
        prec_val = precision_score(y_val, p_val, zero_division=0)
        prec_test = precision_score(y_test, p_test, zero_division=0)
        f1_v = f1_score(y_val, p_val, zero_division=0)
        f1_t = f1_score(y_test, p_test, zero_division=0)
        acc_v = accuracy_score(y_val, p_val)
        acc_t = accuracy_score(y_test, p_test)

        tn_v, fp_v, fn_v, tp_v = confusion_matrix(y_val, p_val).ravel()
        tn_t, fp_t, fn_t, tp_t = confusion_matrix(y_test, p_test).ravel()

        thresh_results.append({
            "Operating Point": label,
            "Threshold": tau,
            "Val Recall": round(float(rec_val), 4),
            "Test Recall": round(float(rec_test), 4),
            "Delta Recall": round(float(rec_test - rec_val), 4),
            "Val Precision": round(float(prec_val), 4),
            "Test Precision": round(float(prec_test), 4),
            "Delta Prec": round(float(prec_test - prec_val), 4),
            "Val F1": round(float(f1_v), 4),
            "Test F1": round(float(f1_t), 4),
            "Delta F1": round(float(f1_t - f1_v), 4),
            "Val Acc": round(float(acc_v), 4),
            "Test Acc": round(float(acc_t), 4),
            "Val (TN/FP/FN/TP)": f"{tn_v}/{fp_v}/{fn_v}/{tp_v}",
            "Test (TN/FP/FN/TP)": f"{tn_t}/{fp_t}/{fn_t}/{tp_t}"
        })

    df_thresh = pd.DataFrame(thresh_results)
    print("\n" + "=" * 80)
    print(" OPERATING POINT COMPARISON: VALIDATION vs TEST")
    print("=" * 80)
    print(df_thresh[["Operating Point", "Val Recall", "Test Recall", "Val Precision", "Test Precision", "Val F1", "Test F1", "Test (TN/FP/FN/TP)"]].to_string(index=False))

    # 7. Multiclass Evaluation
    val_acc_m = accuracy_score(y_val_idx, val_preds_multi)
    test_acc_m = accuracy_score(y_test_idx, test_preds_multi)
    val_macro_m = f1_score(y_val_idx, val_preds_multi, average="macro", zero_division=0)
    test_macro_m = f1_score(y_test_idx, test_preds_multi, average="macro", zero_division=0)
    val_weight_m = f1_score(y_val_idx, val_preds_multi, average="weighted", zero_division=0)
    test_weight_m = f1_score(y_test_idx, test_preds_multi, average="weighted", zero_division=0)
    val_ll_m = log_loss(y_val_idx, val_probs_multi)
    test_ll_m = log_loss(y_test_idx, test_probs_multi)

    print("\n" + "=" * 80)
    print(" 11-CLASS SCENARIO ATTRIBUTION: VALIDATION vs TEST")
    print("=" * 80)
    print(f"Top-1 Accuracy: Validation = {val_acc_m:.4f} | Test = {test_acc_m:.4f} (Delta = {test_acc_m - val_acc_m:+.4f})")
    print(f"Macro F1-Score: Validation = {val_macro_m:.4f} | Test = {test_macro_m:.4f} (Delta = {test_macro_m - val_macro_m:+.4f})")
    print(f"Weighted F1:    Validation = {val_weight_m:.4f} | Test = {test_weight_m:.4f} (Delta = {test_weight_m - val_weight_m:+.4f})")
    print(f"Log-Loss:       Validation = {val_ll_m:.4f} | Test = {test_ll_m:.4f} (Delta = {test_ll_m - val_ll_m:+.4f})")

    rep_test = classification_report(y_test_idx, test_preds_multi, target_names=classes, digits=4, zero_division=0)
    print("\nPer-Scenario Performance Breakdown on Test Partition:")
    print(rep_test)

    # 8. SHAP Explainability on Test Partition
    print("\n" + "=" * 80)
    print(" TEST PARTITION TREE SHAP FEATURE ATTRIBUTIONS (N=1,500)")
    print("=" * 80)
    dtest = xgb.DMatrix(X_test, feature_names=all_feature_names)
    contribs_test = xgb_clf.get_booster().predict(dtest, pred_contribs=True)
    shap_test = contribs_test[:, :-1]
    mean_shap_test = np.mean(np.abs(shap_test), axis=0)
    top_shap_idx = np.argsort(mean_shap_test)[::-1][:15]

    df_shap_test = pd.DataFrame({
        "Feature": [all_feature_names[i] for i in top_shap_idx],
        "Mean |SHAP| (Test)": [round(float(mean_shap_test[i]), 5) for i in top_shap_idx]
    })
    print(df_shap_test.to_string(index=False))

    # 9. Serialize Production Artifacts
    print("\n" + "=" * 80)
    print(" SERIALIZING PRODUCTION ARTIFACTS")
    print("=" * 80)

    xgb_model_path = "models/aquasynex_xgb_binary_v1.json"
    cat_model_path = "models/aquasynex_catboost_multiclass_v1.cbm"
    preprocessor_path = "models/preprocessor_v1.joblib"
    metadata_path = "models/model_metadata.json"

    # Save exact XGBoost model via native booster JSON
    xgb_clf.get_booster().save_model(xgb_model_path)
    print(f"[+] Saved XGBoost binary model to: {xgb_model_path}")

    # Save exact CatBoost multiclass model
    cat_multi.save_model(cat_model_path)
    print(f"[+] Saved CatBoost multiclass model to: {cat_model_path}")

    # Save exact Preprocessor bundle
    preprocessor_bundle = {
        "scaler": scaler,
        "ohe": ohe,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "all_feature_names": all_feature_names,
        "canonical_features": canonical_features,
        "target_classes_multiclass": classes,
        "fit_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fit_dataset": "data/processed/modeling_v2/modeling_dataset.parquet",
        "training_partition_rows": len(df_train)
    }
    joblib.dump(preprocessor_bundle, preprocessor_path)
    print(f"[+] Saved preprocessor bundle to: {preprocessor_path}")

    # Compute checksums
    checksum_xgb = sha256_checksum(xgb_model_path)
    checksum_cat = sha256_checksum(cat_model_path)
    checksum_prep = sha256_checksum(preprocessor_path)

    # 10. Generate Production Metadata
    metadata = {
        "model_version": "1.0.0",
        "release_tag": "Phase2.7-Production-Freeze",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": {
            "source": "data/processed/modeling_v2/modeling_dataset.parquet",
            "version": "2.0.0",
            "benchmark_type": "Hardened Synthetic Benchmark (v2)",
            "total_records": len(df),
            "train_rows": len(df_train),
            "val_rows": len(df_val),
            "test_rows": len(df_test)
        },
        "artifacts": {
            "xgb_binary_model": {
                "path": xgb_model_path,
                "sha256": checksum_xgb,
                "library": "xgboost",
                "version": xgb.__version__
            },
            "catboost_multiclass_model": {
                "path": cat_model_path,
                "sha256": checksum_cat,
                "library": "catboost",
                "version": "1.2.7"
            },
            "preprocessor": {
                "path": preprocessor_path,
                "sha256": checksum_prep,
                "library": "joblib / scikit-learn",
                "version": "1.5.3"
            }
        },
        "features": {
            "canonical_input_count": len(canonical_features),
            "numeric_count": len(numeric_cols),
            "categorical_count": len(categorical_cols),
            "post_transform_dimension": len(all_feature_names),
            "canonical_names": canonical_features,
            "transformed_names": all_feature_names
        },
        "operating_points": {
            "default_tau_0_50": {
                "threshold": 0.50,
                "val_metrics": {"recall": df_thresh.loc[0, "Val Recall"], "precision": df_thresh.loc[0, "Val Precision"], "f1": df_thresh.loc[0, "Val F1"]},
                "test_metrics": {"recall": df_thresh.loc[0, "Test Recall"], "precision": df_thresh.loc[0, "Test Precision"], "f1": df_thresh.loc[0, "Test F1"]}
            },
            "f1_optimal_tau_0_32": {
                "threshold": 0.32,
                "val_metrics": {"recall": df_thresh.loc[1, "Val Recall"], "precision": df_thresh.loc[1, "Val Precision"], "f1": df_thresh.loc[1, "Val F1"]},
                "test_metrics": {"recall": df_thresh.loc[1, "Test Recall"], "precision": df_thresh.loc[1, "Test Precision"], "f1": df_thresh.loc[1, "Test F1"]}
            },
            "high_precision_r95_tau_0_67": {
                "threshold": 0.67,
                "val_metrics": {"recall": df_thresh.loc[2, "Val Recall"], "precision": df_thresh.loc[2, "Val Precision"], "f1": df_thresh.loc[2, "Val F1"]},
                "test_metrics": {"recall": df_thresh.loc[2, "Test Recall"], "precision": df_thresh.loc[2, "Test Precision"], "f1": df_thresh.loc[2, "Test F1"]}
            }
        },
        "temporal_generalization": {
            "roc_auc": {"val": round(val_roc, 4), "test": round(test_roc, 4), "delta": round(delta_roc, 4)},
            "pr_auc": {"val": round(val_pr, 4), "test": round(test_pr, 4), "delta": round(delta_pr, 4)},
            "multiclass_accuracy": {"val": round(val_acc_m, 4), "test": round(test_acc_m, 4), "delta": round(test_acc_m - val_acc_m, 4)},
            "multiclass_macro_f1": {"val": round(val_macro_m, 4), "test": round(test_macro_m, 4), "delta": round(test_macro_m - val_macro_m, 4)}
        },
        "scientific_disclaimer": (
            "All metrics were evaluated on the AquaSynex hardened synthetic development benchmark (v2.0.0). "
            "These results validate the algorithmic integrity and UTXO topological graph features, but do NOT "
            "constitute proof of real-world Bitcoin criminal detection without validation on empirical public ledgers."
        )
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Saved production metadata & checksums to: {metadata_path}")

    print("\n[*] Running production artifact roundtrip deserialization test...")
    loaded_booster = xgb.Booster()
    loaded_booster.load_model(xgb_model_path)
    loaded_prep = joblib.load(preprocessor_path)

    # Test on first 10 rows of test partition
    sample_df = df_test.iloc[:10]
    sample_num = loaded_prep["scaler"].transform(sample_df[loaded_prep["numeric_cols"]])
    sample_cat = loaded_prep["ohe"].transform(sample_df[loaded_prep["categorical_cols"]])
    sample_X = np.hstack([sample_num, sample_cat])

    orig_sample_probs = test_probs_binary[:10]
    d_sample = xgb.DMatrix(sample_X, feature_names=all_feature_names)
    loaded_sample_probs = loaded_booster.predict(d_sample)

    max_diff = np.max(np.abs(orig_sample_probs - loaded_sample_probs))
    if max_diff < 1e-6:
        print(f"[+] Roundtrip test passed: max difference = {max_diff:.2e} (< 1e-6 tolerance).")
    else:
        raise ValueError(f"Roundtrip test failed: max difference = {max_diff:.2e}")

    print("\n" + "=" * 80)
    print(" PHASE 2.7 FINAL TEST EVALUATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
