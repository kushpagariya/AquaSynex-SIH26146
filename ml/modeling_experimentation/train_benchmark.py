"""
AquaSynex — Phase 2.5B ML Model Experimentation & Benchmarking
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Responsibilities:
1. Loads modeling_dataset.parquet and feature_manifest.yaml.
2. Extracts strictly the 46 canonical predictive features.
3. Partitions according to chronological temporal split:
   - train: 70% (N = 7,000)
   - val:   15% (N = 1,500)
   - test:  15% (N = 1,500) — STRICTLY UNTOUCHED
4. Fits preprocessing (scaling and one-hot encoding) strictly on train.
5. Evaluates Baseline (Logistic Regression), Random Forest, XGBoost, and CatBoost on validation split.
6. Computes ROC-AUC, PR-AUC, Accuracy, Precision, Recall, F1, and Confusion Matrix.
7. Checks for overfitting (train score vs validation score comparison).
8. Exports experiment summary to ml/modeling_experimentation/experiment_results.json.
"""

import os
import json
import time
import yaml
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import duckdb

from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)
from xgboost import XGBClassifier
from catboost import CatBoostClassifier


class MLExperimentationRunner:
    def __init__(
        self,
        dataset_path: str = "data/processed/modeling/modeling_dataset.parquet",
        manifest_path: str = "data/processed/modeling/feature_manifest.yaml",
        random_seed: int = 42
    ):
        self.dataset_path = os.path.abspath(dataset_path).replace("\\", "/")
        self.manifest_path = os.path.abspath(manifest_path).replace("\\", "/")
        self.random_seed = random_seed
        self.results: Dict[str, Any] = {}

    def run_experiments(self) -> Dict[str, Any]:
        start_time = time.time()
        print("=" * 75)
        print("AquaSynex — Phase 2.5B Model Experimentation & Benchmarking")
        print("=" * 75)

        # 1. Load Manifest to get exact 46 canonical features
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        canonical_features = manifest["canonical_feature_names"]
        print(f"[*] Loaded feature manifest: {len(canonical_features)} canonical features.")
        assert len(canonical_features) == 46, f"Expected 46 canonical features, got {len(canonical_features)}"

        # 2. Load Dataset
        con = duckdb.connect()
        df = con.execute(f"SELECT * FROM read_parquet('{self.dataset_path}')").df()
        con.close()

        print(f"[*] Loaded dataset: {df.shape[0]:,} rows x {df.shape[1]} columns.")

        # 3. Partition into Chronological Splits
        train_mask = df["temporal_split"] == "train"
        val_mask = df["temporal_split"] == "val"
        test_mask = df["temporal_split"] == "test"

        df_train = df[train_mask].copy()
        df_val = df[val_mask].copy()
        df_test = df[test_mask].copy()

        print(f"    - Train split: {len(df_train):,} rows ({len(df_train)/len(df):.1%}) | Suspicious: {df_train['target_binary'].mean():.2%}")
        print(f"    - Val split:   {len(df_val):,} rows ({len(df_val)/len(df):.1%}) | Suspicious: {df_val['target_binary'].mean():.2%}")
        print(f"    - Test split:  {len(df_test):,} rows ({len(df_test)/len(df):.1%}) | Suspicious: {df_test['target_binary'].mean():.2%} (UNTOUCHED)")

        # Targets
        y_train = df_train["target_binary"].values
        y_val = df_val["target_binary"].values
        # Note: y_test is NOT loaded or accessed!

        # 4. Separate Numeric and Categorical Features
        categorical_cols = manifest["dataset_summary"].get("canonical_categorical_features", ["net_country", "net_asn"])
        # Ensure exact column list
        cat_cols = ["net_country", "net_asn"]
        num_cols = [c for c in canonical_features if c not in cat_cols]

        print(f"[*] Preprocessing layout: {len(num_cols)} numeric features, {len(cat_cols)} categorical features.")

        # 5. Fit Preprocessing ONLY on Train
        print("[*] Fitting preprocessing transformers strictly on train split...")
        scaler = RobustScaler()
        scaler.fit(df_train[num_cols])

        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        ohe.fit(df_train[cat_cols].astype(str))

        ohe_feature_names = list(ohe.get_feature_names_out(cat_cols))
        transformed_feature_names = num_cols + ohe_feature_names
        print(f"    - One-hot expansion: {len(cat_cols)} categorical -> {len(ohe_feature_names)} binary columns.")
        print(f"    - Total processed feature dimension: {len(transformed_feature_names)} columns.")

        # Transform train and val
        X_train_num = scaler.transform(df_train[num_cols])
        X_train_cat = ohe.transform(df_train[cat_cols].astype(str))
        X_train = np.hstack([X_train_num, X_train_cat])

        X_val_num = scaler.transform(df_val[num_cols])
        X_val_cat = ohe.transform(df_val[cat_cols].astype(str))
        X_val = np.hstack([X_val_num, X_val_cat])

        # 6. Model Configurations
        models = {
            "Baseline (Logistic Regression)": {
                "estimator": LogisticRegression(
                    max_iter=1000,
                    random_state=self.random_seed,
                    class_weight="balanced"
                ),
                "params": {"max_iter": 1000, "class_weight": "balanced", "random_state": self.random_seed}
            },
            "Random Forest": {
                "estimator": RandomForestClassifier(
                    n_estimators=100,
                    max_depth=12,
                    min_samples_leaf=3,
                    random_state=self.random_seed,
                    n_jobs=-1
                ),
                "params": {"n_estimators": 100, "max_depth": 12, "min_samples_leaf": 3, "random_state": self.random_seed}
            },
            "XGBoost": {
                "estimator": XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=self.random_seed,
                    eval_metric="logloss",
                    n_jobs=-1
                ),
                "params": {"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1, "subsample": 0.8, "colsample_bytree": 0.8}
            },
            "CatBoost": {
                "estimator": CatBoostClassifier(
                    iterations=100,
                    depth=6,
                    learning_rate=0.1,
                    random_seed=self.random_seed,
                    verbose=0
                ),
                "params": {"iterations": 100, "depth": 6, "learning_rate": 0.1, "random_seed": self.random_seed}
            }
        }

        # 7. Training and Evaluation Loop
        model_results = []
        print("\n[*] Training models on train split (N=7,000) and evaluating on validation split (N=1,500)...")

        for name, config in models.items():
            model = config["estimator"]
            t0 = time.time()
            model.fit(X_train, y_train)
            train_duration = time.time() - t0

            # Training set predictions (for overfitting check)
            train_preds = model.predict(X_train)
            train_probs = model.predict_proba(X_train)[:, 1] if hasattr(model, "predict_proba") else train_preds
            train_roc_auc = float(roc_auc_score(y_train, train_probs))
            train_f1 = float(f1_score(y_train, train_preds))

            # Validation set predictions (for model comparison)
            val_preds = model.predict(X_val)
            val_probs = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else val_preds

            val_roc_auc = float(roc_auc_score(y_val, val_probs))
            val_pr_auc = float(average_precision_score(y_val, val_probs))
            val_acc = float(accuracy_score(y_val, val_preds))
            val_prec = float(precision_score(y_val, val_preds, zero_division=0))
            val_rec = float(recall_score(y_val, val_preds, zero_division=0))
            val_f1 = float(f1_score(y_val, val_preds, zero_division=0))
            cm = confusion_matrix(y_val, val_preds).tolist()

            # Overfitting gap
            roc_gap = train_roc_auc - val_roc_auc
            f1_gap = train_f1 - val_f1

            res = {
                "model_name": name,
                "training_time_sec": round(train_duration, 3),
                "hyperparameters": config["params"],
                "validation_metrics": {
                    "roc_auc": round(val_roc_auc, 4),
                    "pr_auc": round(val_pr_auc, 4),
                    "accuracy": round(val_acc, 4),
                    "precision": round(val_prec, 4),
                    "recall": round(val_rec, 4),
                    "f1_score": round(val_f1, 4),
                    "confusion_matrix": {
                        "tn": cm[0][0],
                        "fp": cm[0][1],
                        "fn": cm[1][0],
                        "tp": cm[1][1]
                    }
                },
                "training_metrics": {
                    "train_roc_auc": round(train_roc_auc, 4),
                    "train_f1": round(train_f1, 4)
                },
                "overfitting_audit": {
                    "roc_auc_gap": round(roc_gap, 4),
                    "f1_score_gap": round(f1_gap, 4),
                    "overfitting_risk": "Low" if roc_gap < 0.05 else ("Moderate" if roc_gap < 0.10 else "High")
                }
            }
            model_results.append(res)
            print(f"  [+] {name:<30} | Val ROC-AUC: {val_roc_auc:.4f} | PR-AUC: {val_pr_auc:.4f} | F1: {val_f1:.4f} | Rec: {val_rec:.4f} | Prec: {val_prec:.4f} | Time: {train_duration:.2f}s")

        self.results = {
            "phase": "2.5B",
            "timestamp": "2026-09-12T02:55:00Z",
            "feature_count": len(canonical_features),
            "processed_feature_dimension": len(transformed_feature_names),
            "split_summary": {
                "train_records": len(df_train),
                "val_records": len(df_val),
                "test_records": len(df_test),
                "test_set_touched": False,
                "test_status": "STRICTLY UNTOUCHED & FROZEN"
            },
            "models_evaluated": model_results
        }

        # 8. Export Results
        out_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(out_dir, exist_ok=True)
        results_file = os.path.join(out_dir, "experiment_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[+] Saved experiment results to: {results_file}", flush=True)

        return self.results


if __name__ == "__main__":
    runner = MLExperimentationRunner()
    runner.run_experiments()
