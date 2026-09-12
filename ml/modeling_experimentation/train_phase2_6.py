"""
AquaSynex — Phase 2.6 Modeling & Validation Runner (Diagnostic / Local Verification)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Executes the candidate model comparison on the hardened v2 synthetic benchmark:
1. Candidate Models: Random Forest, XGBoost, CatBoost
2. Chronological Splits: Train (N=7,000), Validation (N=1,500).
   TEST PARTITION (N=1,500) IS STRICTLY FROZEN & UNTOUCHED.
3. Threshold Calibration: Default (0.50), F1-Optimal, and Deterministic R95.
4. Secondary 11-Class Multiclass Experiment.
5. SHAP Analysis: Computed strictly for the selected provisional best binary model.

NOTE: This script produces local diagnostic results. The authoritative official
results reside in notebooks/08_official_colab_modeling.ipynb.
"""

import os
import time
import json
import yaml
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import duckdb

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
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


class Phase26ModelingExperiment:
    def __init__(
        self,
        dataset_path: str = "data/processed/modeling_v2/modeling_dataset.parquet",
        manifest_path: str = "data/processed/modeling_v2/feature_manifest.yaml",
        output_json: str = "ml/modeling_experimentation/phase2_6_model_selection_results.json",
        random_seed: int = 42
    ):
        self.dataset_path = os.path.abspath(dataset_path).replace("\\", "/")
        self.manifest_path = os.path.abspath(manifest_path).replace("\\", "/")
        self.output_json = os.path.abspath(output_json).replace("\\", "/")
        self.random_seed = random_seed
        self.results: Dict[str, Any] = {"environment": "local_diagnostic", "phase": "2.6"}

    def run(self) -> Dict[str, Any]:
        start_time = time.time()
        print("=" * 80)
        print("AquaSynex — Phase 2.6 Modeling Experimentation (Hardened v2 Benchmark)")
        print("=" * 80)

        # 1. Load Feature Manifest & Dataset
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        canonical_features = manifest["canonical_feature_names"]
        categorical_cols = ["net_country", "net_asn"]
        numeric_cols = [c for c in canonical_features if c not in categorical_cols]
        assert len(canonical_features) == 46, f"Expected 46 canonical features, got {len(canonical_features)}"

        con = duckdb.connect()
        df = con.execute(f"SELECT * FROM read_parquet('{self.dataset_path}')").df()
        con.close()

        # 2. Strict Partitioning (Test set strictly quarantined)
        df_train = df[df["temporal_split"] == "train"].copy()
        df_val = df[df["temporal_split"] == "val"].copy()
        df_test = df[df["temporal_split"] == "test"].copy()

        y_train = df_train["target_binary"].values
        y_val = df_val["target_binary"].values

        y_train_multi = df_train["target_multiclass"].values
        y_val_multi = df_val["target_multiclass"].values

        print(f"[*] Dataset Partitions:")
        print(f"    - Train (N={len(df_train):,}): Suspicious = {y_train.mean():.2%}")
        print(f"    - Val   (N={len(df_val):,}): Suspicious = {y_val.mean():.2%}")
        print(f"    - Test  (N={len(df_test):,}): [STRICTLY FROZEN & UNTOUCHED]")

        # 3. Fit Preprocessing Strictly on Train Only
        print("\n[*] Fitting preprocessors strictly on Train partition...")
        scaler = RobustScaler()
        X_train_num = scaler.fit_transform(df_train[numeric_cols])
        X_val_num = scaler.transform(df_val[numeric_cols])

        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        X_train_cat = ohe.fit_transform(df_train[categorical_cols])
        X_val_cat = ohe.transform(df_val[categorical_cols])

        cat_feature_names = list(ohe.get_feature_names_out(categorical_cols))
        all_feature_names = numeric_cols + cat_feature_names

        X_train = np.hstack([X_train_num, X_train_cat])
        X_val = np.hstack([X_val_num, X_val_cat])
        print(f"[+] Feature matrix assembled: {X_train.shape[1]} features ({len(numeric_cols)} numeric + {len(cat_feature_names)} encoded categorical).")

        # 4. Train Candidate Binary Models
        print("\n[*] Training and Evaluating Candidate Binary Models...")
        models = {
            "Random Forest": RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                min_samples_split=5,
                class_weight="balanced_subsample",
                random_state=self.random_seed,
                n_jobs=-1
            ),
            "XGBoost": XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=float(len(y_train) - sum(y_train)) / sum(y_train),
                eval_metric="logloss",
                random_state=self.random_seed
            ),
            "CatBoost": CatBoostClassifier(
                iterations=400,
                depth=6,
                learning_rate=0.05,
                auto_class_weights="Balanced",
                eval_metric="Logloss",
                random_seed=self.random_seed,
                verbose=0
            )
        }

        binary_evaluations = {}
        val_probs_dict = {}

        for name, model in models.items():
            t0 = time.time()
            model.fit(X_train, y_train)
            fit_time = time.time() - t0

            t_infer = time.time()
            val_probs = model.predict_proba(X_val)[:, 1]
            infer_time_1k = (time.time() - t_infer) / len(X_val) * 1000

            val_preds = (val_probs >= 0.50).astype(int)
            val_probs_dict[name] = val_probs

            roc_auc = float(roc_auc_score(y_val, val_probs))
            pr_auc = float(average_precision_score(y_val, val_probs))
            acc = float(accuracy_score(y_val, val_preds))
            prec = float(precision_score(y_val, val_preds, zero_division=0))
            rec = float(recall_score(y_val, val_preds, zero_division=0))
            f1 = float(f1_score(y_val, val_preds, zero_division=0))
            tn, fp, fn, tp = confusion_matrix(y_val, val_preds).ravel()

            binary_evaluations[name] = {
                "roc_auc": round(roc_auc, 4),
                "pr_auc": round(pr_auc, 4),
                "accuracy": round(acc, 4),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                "fit_time_seconds": round(fit_time, 3),
                "infer_latency_ms_per_1k": round(infer_time_1k * 1000, 2)
            }
            print(f"  -> {name:<14} | ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {f1:.4f} | Recall: {rec:.4f} | Precision: {prec:.4f} | Fit: {fit_time:.2f}s")

        self.results["binary_model_comparisons"] = binary_evaluations

        # 5. Model Selection (Validation Only)
        # Sort by ROC-AUC then PR-AUC
        selected_model_name = max(
            binary_evaluations.keys(),
            key=lambda m: (binary_evaluations[m]["roc_auc"], binary_evaluations[m]["pr_auc"])
        )
        print(f"\n[+] Selected Provisional Best Model: {selected_model_name}")
        self.results["selected_model"] = selected_model_name
        selected_model = models[selected_model_name]
        selected_val_probs = val_probs_dict[selected_model_name]

        # 6. Threshold Calibration (Validation Only)
        print(f"\n[*] Calibrating Decision Thresholds for {selected_model_name}...")
        thresholds = np.arange(0.01, 1.00, 0.01)
        best_f1 = -1.0
        best_f1_tau = 0.50

        r95_candidates = []

        for tau in thresholds:
            p = (selected_val_probs >= tau).astype(int)
            r = recall_score(y_val, p, zero_division=0)
            prec = precision_score(y_val, p, zero_division=0)
            f = f1_score(y_val, p, zero_division=0)

            if f > best_f1:
                best_f1 = f
                best_f1_tau = tau

            if r >= 0.95:
                r95_candidates.append((tau, prec, f, r))

        # Deterministic R95 threshold rule:
        # Among thresholds with Recall >= 0.95, select highest Precision; tie-break highest F1.
        if r95_candidates:
            r95_candidates.sort(key=lambda item: (item[1], item[2]), reverse=True)
            best_r95_tau = r95_candidates[0][0]
        else:
            best_r95_tau = 0.50

        def eval_at_threshold(tau: float) -> Dict[str, Any]:
            p = (selected_val_probs >= tau).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_val, p).ravel()
            return {
                "threshold": round(float(tau), 2),
                "precision": round(float(precision_score(y_val, p, zero_division=0)), 4),
                "recall": round(float(recall_score(y_val, p, zero_division=0)), 4),
                "f1": round(float(f1_score(y_val, p, zero_division=0)), 4),
                "accuracy": round(float(accuracy_score(y_val, p)), 4),
                "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
            }

        threshold_evals = {
            "default_tau_0_50": eval_at_threshold(0.50),
            "f1_optimal_tau": eval_at_threshold(best_f1_tau),
            "high_recall_r95_tau": eval_at_threshold(best_r95_tau)
        }
        self.results["threshold_calibrations"] = threshold_evals

        print(f"    - Default (tau=0.50):    F1={threshold_evals['default_tau_0_50']['f1']:.4f}, Recall={threshold_evals['default_tau_0_50']['recall']:.4f}, Prec={threshold_evals['default_tau_0_50']['precision']:.4f}")
        print(f"    - F1-Optimal (tau={best_f1_tau:.2f}): F1={threshold_evals['f1_optimal_tau']['f1']:.4f}, Recall={threshold_evals['f1_optimal_tau']['recall']:.4f}, Prec={threshold_evals['f1_optimal_tau']['precision']:.4f}")
        print(f"    - R95 Target (tau={best_r95_tau:.2f}): F1={threshold_evals['high_recall_r95_tau']['f1']:.4f}, Recall={threshold_evals['high_recall_r95_tau']['recall']:.4f}, Prec={threshold_evals['high_recall_r95_tau']['precision']:.4f}")

        # 7. Secondary 11-Class Multiclass Experiment
        print("\n[*] Training Secondary 11-Class Multiclass Model (CatBoost)...")
        classes = sorted(list(np.unique(y_train_multi)))
        class_to_idx = {c: i for i, c in enumerate(classes)}
        y_train_idx = np.array([class_to_idx[c] for c in y_train_multi])
        y_val_idx = np.array([class_to_idx[c] for c in y_val_multi])

        multi_model = CatBoostClassifier(
            iterations=350,
            depth=6,
            learning_rate=0.06,
            loss_function="MultiClass",
            eval_metric="MultiClass",
            random_seed=self.random_seed,
            verbose=0
        )
        multi_model.fit(X_train, y_train_idx)
        val_multi_probs = multi_model.predict_proba(X_val)
        val_multi_preds = np.argmax(val_multi_probs, axis=1)

        multi_logloss = float(log_loss(y_val_idx, val_multi_probs))
        multi_acc = float(accuracy_score(y_val_idx, val_multi_preds))
        multi_macro_f1 = float(f1_score(y_val_idx, val_multi_preds, average="macro", zero_division=0))
        multi_weighted_f1 = float(f1_score(y_val_idx, val_multi_preds, average="weighted", zero_division=0))

        report_dict = classification_report(
            y_val_idx,
            val_multi_preds,
            target_names=classes,
            output_dict=True,
            zero_division=0
        )

        self.results["secondary_multiclass_evaluation"] = {
            "model": "CatBoost-MultiClass",
            "accuracy": round(multi_acc, 4),
            "macro_f1": round(multi_macro_f1, 4),
            "weighted_f1": round(multi_weighted_f1, 4),
            "log_loss": round(multi_logloss, 4),
            "per_class_report": {c: {k: round(v, 4) for k, v in report_dict[c].items()} for c in classes}
        }
        print(f"[+] Multiclass Evaluation: Top-1 Acc: {multi_acc:.4f} | Macro F1: {multi_macro_f1:.4f} | Weighted F1: {multi_weighted_f1:.4f} | LogLoss: {multi_logloss:.4f}")

        # 8. SHAP Analysis (Strictly on Selected Binary Model Only)
        if HAS_SHAP:
            print(f"\n[*] Computing SHAP Explainability strictly for selected model ({selected_model_name})...")
            shap_sample_size = min(300, len(X_val))
            sample_idx = np.random.default_rng(self.random_seed).choice(len(X_val), size=shap_sample_size, replace=False)
            X_val_sample = X_val[sample_idx]

            explainer = shap.TreeExplainer(selected_model)
            shap_values = explainer.shap_values(X_val_sample)

            if isinstance(shap_values, list) and len(shap_values) == 2:
                shap_matrix = shap_values[1]
            else:
                shap_matrix = shap_values

            mean_abs_shap = np.mean(np.abs(shap_matrix), axis=0)
            shap_feature_importance = [
                {"feature": all_feature_names[i], "mean_abs_shap": round(float(mean_abs_shap[i]), 5)}
                for i in np.argsort(mean_abs_shap)[::-1][:20]
            ]

            self.results["shap_analysis"] = {
                "selected_model": selected_model_name,
                "sample_size": shap_sample_size,
                "top_20_features": shap_feature_importance
            }
            print(f"[+] SHAP analysis complete for {selected_model_name}:")
            for rank, item in enumerate(shap_feature_importance[:10], 1):
                print(f"    {rank:>2}. {item['feature']:<30}: Mean |SHAP| = {item['mean_abs_shap']:.5f}")
        else:
            print("\n[*] SHAP library not available in local environment; skipping local SHAP (computed in Colab).")

        # 9. Feature Importances (Tree Gain / Gini)
        if hasattr(selected_model, "feature_importances_"):
            importances = selected_model.feature_importances_
            sorted_idx = np.argsort(importances)[::-1]
            top_features = [
                {"feature": all_feature_names[i], "importance": round(float(importances[i]), 5)}
                for i in sorted_idx[:20]
            ]
            self.results["feature_importances"] = top_features

        # 10. Save Results JSON
        os.makedirs(os.path.dirname(self.output_json), exist_ok=True)
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[+] Saved Phase 2.6 local diagnostic results to: {self.output_json}")

        elapsed = time.time() - start_time
        print(f"[+] Phase 2.6 diagnostic execution finished in {elapsed:.2f} seconds.")
        return self.results


if __name__ == "__main__":
    experiment = Phase26ModelingExperiment()
    experiment.run()
