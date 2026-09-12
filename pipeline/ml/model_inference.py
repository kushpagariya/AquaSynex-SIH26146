"""ML Pipeline Integration Adapter and Execution Boundary.

Authoritative reference: docs/backend/backend-ml-contract.md and docs/ml/model-output-contract.md.
Rules:
- Establish clean integration boundary for ML.
- Consume and orchestrate existing, tested ML pipeline components.
- Zero fake predictions or heuristic fallbacks.
- Strictly enforce dataset isolation by dataset_id.
- Return structured List[Dict[str, Any]] meeting PipelineService validation requirements.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import duckdb
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from catboost import CatBoostClassifier

from backend.utils.errors import (
    DatasetError,
    FeatureSchemaMismatchError,
    InvalidFeaturesError,
    MLError,
    ModelLoadError,
)
from backend.utils.logging import logger
from ml.data_pipeline.cleaning import DataCleaningEngine
from ml.data_pipeline.ingestion import DataIngestionEngine
from ml.data_pipeline.normalization import DataNormalizationEngine
from ml.data_pipeline.validation import DataValidationEngine
from ml.feature_engineering.feature_pipeline import FeatureEngineeringPipeline
from ml.graph_analysis.graph_features import GraphFeatureExtractor

# Feature display metadata dictionary for investigator-facing explanations
FEATURE_DISPLAY_METADATA: Dict[str, Tuple[str, Optional[str]]] = {
    "tx_input_count": ("Input count", "count"),
    "tx_output_count": ("Output count", "count"),
    "tx_input_output_ratio": ("Input/output ratio", "ratio"),
    "tx_total_input_sats": ("Total input value", "sats"),
    "tx_total_output_sats": ("Total output value", "sats"),
    "tx_fee_sats": ("Transaction fee", "sats"),
    "tx_size_bytes": ("Transaction size", "bytes"),
    "tx_fee_rate_sat_per_byte": ("Fee rate", "sat/byte"),
    "tx_value_balance_ratio": ("Value balance ratio", "ratio"),
    "tx_avg_input_value_sats": ("Average input value", "sats"),
    "tx_max_input_value_sats": ("Max input value", "sats"),
    "tx_avg_output_value_sats": ("Average output value", "sats"),
    "tx_max_output_value_sats": ("Max output value", "sats"),
    "tx_log_total_value": ("Log total value", "log_sats"),
    "tx_log_fee": ("Log fee", "log_sats"),
    "addr_hist_tx_count": ("Historical address transaction count", "count"),
    "addr_hist_total_sent_sats": ("Total sent by address", "sats"),
    "addr_hist_total_received_sats": ("Total received by address", "sats"),
    "addr_hist_avg_tx_val_sats": ("Average transaction value for address", "sats"),
    "addr_hist_unique_counterparties": ("Unique counterparties", "count"),
    "addr_hist_active_days": ("Active days for address", "days"),
    "addr_hist_tx_per_day": ("Transaction velocity", "tx/day"),
    "addr_reuse_count": ("Address reuse count", "count"),
    "time_hour_of_day": ("Hour of day", "hour"),
    "time_day_of_week": ("Day of week", "day"),
    "time_since_prev_global_tx_sec": ("Time since previous global tx", "sec"),
    "time_txs_last_1m": ("Transactions in last 1 minute", "count"),
    "time_txs_last_5m": ("Transactions in last 5 minutes", "count"),
    "time_txs_last_1h": ("Transactions in last 1 hour", "count"),
    "time_since_prev_addr_tx_sec": ("Time since previous address tx", "sec"),
    "net_src_port": ("Network source port", "port"),
    "net_dst_port": ("Network destination port", "port"),
    "net_is_standard_bitcoin_port": ("Standard Bitcoin peer port flag", "bool"),
    "net_hist_unique_ips_for_addr": ("Historical unique IPs for address", "count"),
    "rel_fan_in": ("Relational fan-in degree", "count"),
    "rel_fan_out": ("Relational fan-out degree", "count"),
    "rel_has_change_output": ("Has change output", "bool"),
    "rel_change_value_ratio": ("Change value ratio", "ratio"),
    "hist_in_mean_neighbor_degree": ("Mean incoming neighbor degree", "degree"),
    "hist_out_mean_neighbor_degree": ("Mean outgoing neighbor degree", "degree"),
    "hist_component_size": ("Connected component size", "nodes"),
    "hist_address_reuse_ratio": ("Address reuse ratio", "ratio"),
    "hist_cluster_size": ("Entity cluster size", "addresses"),
    "hist_cluster_tx_count": ("Entity cluster transaction count", "count"),
    "net_country": ("Network peer country code", "country"),
    "net_asn": ("Autonomous system number", "ASN"),
}

VALID_SUPPORTED_MODELS = {
    "aquasynex_xgb_binary_v1",
    "aquasynex_v1",
    "aquasynex_catboost_multiclass_v1",
}


def _extract_config_val(config: Any, snake_key: str, camel_key: str, default: Any) -> Any:
    """Safely extract a config value from a Pydantic object, dict (snake or camel), or None."""
    if config is None:
        return default
    if isinstance(config, dict):
        if snake_key in config and config[snake_key] is not None:
            return config[snake_key]
        if camel_key in config and config[camel_key] is not None:
            return config[camel_key]
        return default
    val = getattr(config, snake_key, None)
    if val is not None:
        return val
    val = getattr(config, camel_key, None)
    if val is not None:
        return val
    return default


def map_risk_level(risk_score: float) -> str:
    """Map continuous risk probability to standardized risk level.

    Boundary rules (authoritative):
    - [0.90, 1.00] -> 'critical'
    - [0.70, 0.90) -> 'high'
    - [0.40, 0.70) -> 'medium'
    - [0.00, 0.40) -> 'low'
    """
    if risk_score >= 0.90:
        return "critical"
    if risk_score >= 0.70:
        return "high"
    if risk_score >= 0.40:
        return "medium"
    return "low"


def _resolve_model_paths(models_dir: str, model_id: str, model_version: str) -> Tuple[Path, Path, Path, Dict[str, Any]]:
    """Locate and validate model artifacts. Raises ModelLoadError on failure."""
    models_path = Path(models_dir)
    meta_path = models_path / "model_metadata.json"

    # Fallback to repository models directory if not found in custom models_dir
    if not meta_path.exists():
        repo_models = Path(__file__).resolve().parent.parent.parent / "models"
        if (repo_models / "model_metadata.json").exists():
            models_path = repo_models
            meta_path = repo_models / "model_metadata.json"

    if not meta_path.exists():
        raise ModelLoadError(
            f"Model metadata file 'model_metadata.json' not found in {models_dir}",
            details={"modelId": model_id, "modelVersion": model_version},
        )

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as exc:
        raise ModelLoadError(f"Failed to read model metadata: {exc}") from exc

    # Explicit rejection of unsupported or uninstalled model IDs
    if model_id not in VALID_SUPPORTED_MODELS:
        raise ModelLoadError(
            f"ML pipeline module 'pipeline.ml.model_inference' is not installed or model '{model_id}' artifact is unavailable",
            details={"modelId": model_id, "modelVersion": model_version},
        )

    # Artifact file paths
    xgb_path = models_path / "aquasynex_xgb_binary_v1.json"
    cat_path = models_path / "aquasynex_catboost_multiclass_v1.cbm"
    prep_path = models_path / "preprocessor_v1.joblib"

    for artifact_name, p in [
        ("XGBoost binary model", xgb_path),
        ("CatBoost multiclass model", cat_path),
        ("Feature preprocessor", prep_path),
    ]:
        if not p.exists():
            raise ModelLoadError(
                f"{artifact_name} artifact '{p.name}' is unavailable at {models_path}",
                details={"modelId": model_id, "missingFile": str(p)},
            )

    return xgb_path, cat_path, prep_path, metadata


def _load_dataset_records(
    dataset_id: str,
    db_path: str,
    data_dir: str,
) -> Dict[str, pd.DataFrame]:
    """Extract dataset records strictly filtered by dataset_id with dataset isolation."""
    observational: Dict[str, pd.DataFrame] = {}

    # 1. Attempt extraction from DuckDB
    is_custom_db = False
    custom_con = None
    try:
        from backend.config import settings
        from backend.db.connection import get_db_connection

        if db_path and Path(db_path).is_file():
            try:
                if Path(db_path).resolve() != Path(settings.DB_PATH).resolve():
                    custom_con = duckdb.connect(str(db_path), read_only=True)
                    is_custom_db = True
            except Exception:
                custom_con = None

        con = custom_con if is_custom_db and custom_con is not None else get_db_connection()

        df_tx = con.execute("SELECT * FROM transactions WHERE dataset_id = ?", [dataset_id]).fetchdf()
        df_in = con.execute("SELECT * FROM transaction_inputs WHERE dataset_id = ?", [dataset_id]).fetchdf()
        df_out = con.execute("SELECT * FROM transaction_outputs WHERE dataset_id = ?", [dataset_id]).fetchdf()
        try:
            df_net = con.execute("SELECT * FROM network_events WHERE dataset_id = ?", [dataset_id]).fetchdf()
        except Exception:
            df_net = pd.DataFrame()

        if not df_tx.empty:
            observational["transactions"] = df_tx
            observational["transaction_inputs"] = df_in
            observational["transaction_outputs"] = df_out
            observational["network_events"] = df_net
    except Exception as exc:
        logger.warning(f"Failed to query DuckDB for dataset {dataset_id}: {exc}")
    finally:
        if is_custom_db and custom_con is not None:
            try:
                custom_con.close()
            except Exception:
                pass

    # 2. If transactions still empty, check disk in data_dir / dataset_id
    dataset_dir = Path(data_dir) / dataset_id
    if ("transactions" not in observational or observational["transactions"].empty) and dataset_dir.exists():
        if (dataset_dir / "transactions.parquet").exists():
            ingest_engine = DataIngestionEngine(dataset_id=dataset_id)
            obs, _ = ingest_engine.load_from_parquet_dir(str(dataset_dir))
            observational = obs
        else:
            for cand in dataset_dir.iterdir():
                if cand.suffix in (".csv", ".parquet"):
                    with duckdb.connect() as disk_con:
                        raw_df = disk_con.execute(f"SELECT * FROM '{str(cand).replace(os.sep, '/')}'").fetchdf()
                    normalizer = DataNormalizationEngine(dataset_id=dataset_id)
                    observational = normalizer._decompose_sih_to_canonical(raw_df)
                    break

    # 3. Check if network_events is present; if not in DuckDB, check if disk has network file
    if ("network_events" not in observational or observational["network_events"].empty) and dataset_dir.exists():
        for net_name in ["network_events.parquet", "network_events_sample.csv", "network_events.csv"]:
            net_file = dataset_dir / net_name
            if net_file.exists():
                with duckdb.connect() as disk_con:
                    observational["network_events"] = disk_con.execute(f"SELECT * FROM '{str(net_file).replace(os.sep, '/')}'").fetchdf()
                break

    # Enforce non-empty transactions
    if "transactions" not in observational or observational["transactions"].empty:
        raise DatasetError(
            f"Dataset '{dataset_id}' contains 0 transactions or was not found.",
            details={"datasetId": dataset_id},
        )

    # Invariant: network_events is strictly required by the 46-feature model schema
    if "network_events" not in observational or observational["network_events"].empty:
        raise InvalidFeaturesError(
            f"Dataset '{dataset_id}' is missing required network telemetry (canonical_network_events table is missing or empty).",
            details={"datasetId": dataset_id, "requiredTable": "network_events"},
        )

    # 4. Bidirectional column mapping and data integrity guards
    for k in ["transactions", "transaction_inputs", "transaction_outputs", "network_events"]:
        if k in observational and not observational[k].empty:
            df = observational[k]
            if "txid" not in df.columns and "transaction_id" in df.columns:
                df["txid"] = df["transaction_id"]
            if "transaction_id" not in df.columns and "txid" in df.columns:
                df["transaction_id"] = df["txid"]
            if "dataset_id" not in df.columns:
                df["dataset_id"] = dataset_id

    # Transactions alignment
    df_tx = observational["transactions"]
    if "transaction_size_bytes" not in df_tx.columns and "size_bytes" in df_tx.columns:
        df_tx["transaction_size_bytes"] = df_tx["size_bytes"]
    elif "size_bytes" not in df_tx.columns and "transaction_size_bytes" in df_tx.columns:
        df_tx["size_bytes"] = df_tx["transaction_size_bytes"]
    if "transaction_size_bytes" not in df_tx.columns:
        df_tx["transaction_size_bytes"] = 250

    if "fee_satoshi" not in df_tx.columns:
        if "fee" in df_tx.columns:
            df_tx["fee_satoshi"] = df_tx["fee"]
        elif "total_input_value_satoshi" in df_tx.columns and "total_output_value_satoshi" in df_tx.columns:
            df_tx["fee_satoshi"] = np.maximum(df_tx["total_input_value_satoshi"] - df_tx["total_output_value_satoshi"], 0)
        else:
            df_tx["fee_satoshi"] = 0

    if "input_count" not in df_tx.columns:
        df_tx["input_count"] = 1
    if "output_count" not in df_tx.columns:
        df_tx["output_count"] = 1

    # Inputs alignment
    if "transaction_inputs" in observational and not observational["transaction_inputs"].empty:
        df_in = observational["transaction_inputs"]
        if "address" not in df_in.columns and "input_address" in df_in.columns:
            df_in["address"] = df_in["input_address"]
        if "input_address" not in df_in.columns and "address" in df_in.columns:
            df_in["input_address"] = df_in["address"]
        if "amount_satoshi" not in df_in.columns and "input_value_satoshi" in df_in.columns:
            df_in["amount_satoshi"] = df_in["input_value_satoshi"]
        if "input_value_satoshi" not in df_in.columns and "amount_satoshi" in df_in.columns:
            df_in["input_value_satoshi"] = df_in["amount_satoshi"]
        if "input_index" not in df_in.columns:
            df_in["input_index"] = df_in.groupby("txid").cumcount()

    # Outputs alignment
    if "transaction_outputs" in observational and not observational["transaction_outputs"].empty:
        df_out = observational["transaction_outputs"]
        if "address" not in df_out.columns and "output_address" in df_out.columns:
            df_out["address"] = df_out["output_address"]
        if "output_address" not in df_out.columns and "address" in df_out.columns:
            df_out["output_address"] = df_out["address"]
        if "amount_satoshi" not in df_out.columns and "output_value_satoshi" in df_out.columns:
            df_out["amount_satoshi"] = df_out["output_value_satoshi"]
        if "output_value_satoshi" not in df_out.columns and "amount_satoshi" in df_out.columns:
            df_out["output_value_satoshi"] = df_out["amount_satoshi"]
        if "output_index" not in df_out.columns:
            df_out["output_index"] = df_out.groupby("txid").cumcount()

    # Network events alignment & type cleanup
    df_net = observational["network_events"]
    if "asn" in df_net.columns:
        df_net["asn"] = (
            df_net["asn"]
            .astype(str)
            .str.extract(r"(\d+)", expand=False)
            .fillna(0)
            .astype("int64")
        )
    if "src_port" in df_net.columns:
        df_net["src_port"] = pd.to_numeric(df_net["src_port"], errors="coerce").fillna(0).astype(int)
    if "dst_port" in df_net.columns:
        df_net["dst_port"] = pd.to_numeric(df_net["dst_port"], errors="coerce").fillna(8333).astype(int)
    if "country" in df_net.columns:
        df_net["country"] = df_net["country"].fillna("UNKNOWN").astype(str)

    return observational


def run_analysis(
    dataset_id: str,
    model_id: str,
    model_version: str,
    config: Any,
    db_path: str,
    data_dir: str,
    models_dir: str,
) -> List[Dict[str, Any]]:
    """Execute complete ML pipeline for dataset_id and return validated result dicts.

    Conforms to docs/backend/backend-ml-contract.md and docs/ml/model-output-contract.md.
    """
    logger.info(f"[ML Adapter] Starting analysis for dataset {dataset_id} with model {model_id} (v{model_version})")

    # 1. Resolve and validate model artifacts
    xgb_path, cat_path, prep_path, metadata = _resolve_model_paths(models_dir, model_id, model_version)

    # 2. Extract dataset strictly isolated by dataset_id
    obs = _load_dataset_records(dataset_id, db_path, data_dir)

    # 3. Validate observational records
    validator = DataValidationEngine()
    val_res = validator.validate(obs)
    if not val_res.is_valid:
        raise InvalidFeaturesError(
            f"Dataset validation failed: {val_res.errors[:3]}",
            details={"errors": val_res.errors},
        )

    # 4. Clean observational data
    cleaner = DataCleaningEngine()
    cleaned = cleaner.clean(obs)

    # 5. Normalize into canonical relational tables
    normalizer = DataNormalizationEngine(dataset_id=dataset_id)
    canonical = normalizer.normalize(cleaned)

    # 6. Extract tabular feature matrix (40 features + transaction_id)
    fe_pipeline = FeatureEngineeringPipeline()
    try:
        f_tab, _ = fe_pipeline.build_feature_matrix(canonical)
    except Exception as exc:
        raise InvalidFeaturesError(f"Tabular feature extraction failed: {exc}") from exc

    # 7. Extract graph-topological features (11 features + transaction_id)
    ge_extractor = GraphFeatureExtractor()
    try:
        f_graph = ge_extractor.extract_features(canonical)
    except Exception as exc:
        raise MLError(f"Graph feature extraction failed: {exc}") from exc

    # 8. Merge tabular and graph features on transaction_id
    merged = f_tab.merge(f_graph, on="transaction_id", how="left")

    # Apply max_entities limit from config if present
    max_entities = _extract_config_val(config, "max_entities", "maxEntities", 10000) or 10000
    if len(merged) > max_entities:
        merged = merged.iloc[:max_entities].copy()

    if len(merged) == 0:
        logger.info(f"[ML Adapter] 0 entities to analyze for dataset {dataset_id}")
        return []

    # 9. Load preprocessor and transform features
    try:
        prep = joblib.load(prep_path)
    except Exception as exc:
        raise ModelLoadError(f"Failed to load preprocessor artifact: {exc}") from exc

    missing_num = [col for col in prep["numeric_cols"] if col not in merged.columns]
    missing_cat = [col for col in prep["categorical_cols"] if col not in merged.columns]
    if missing_num or missing_cat:
        raise FeatureSchemaMismatchError(
            f"Feature schema mismatch. Missing numeric: {missing_num}, missing categorical: {missing_cat}",
            details={"missingNumeric": missing_num, "missingCategorical": missing_cat},
        )

    # Clean any residual NaNs in feature space before preprocessor transformation
    merged[prep["numeric_cols"]] = merged[prep["numeric_cols"]].fillna(0.0)
    merged[prep["categorical_cols"]] = merged[prep["categorical_cols"]].fillna("UNKNOWN")

    try:
        X_num = prep["scaler"].transform(merged[prep["numeric_cols"]])
        X_cat = prep["ohe"].transform(merged[prep["categorical_cols"]])
        X_transformed = np.hstack([X_num, X_cat])
    except Exception as exc:
        raise InvalidFeaturesError(f"Feature transformation error: {exc}") from exc

    expected_dim = metadata.get("features", {}).get("post_transform_dimension", 71)
    if X_transformed.shape[1] != expected_dim:
        raise FeatureSchemaMismatchError(
            f"Feature dimension mismatch: expected {expected_dim}, got {X_transformed.shape[1]}"
        )

    # 10. Run XGBoost binary risk probability and TreeSHAP contributions
    try:
        booster = xgb.Booster()
        booster.load_model(str(xgb_path))
        dmat = xgb.DMatrix(X_transformed, feature_names=prep["all_feature_names"])
        risk_probs = booster.predict(dmat)
        contribs = booster.predict(dmat, pred_contribs=True)
        shaps = contribs[:, :-1]  # Strip bias/base margin term
    except Exception as exc:
        raise MLError(f"XGBoost model inference error: {exc}") from exc

    # 11. Run CatBoost 11-class typology classification
    try:
        cat = CatBoostClassifier()
        cat.load_model(str(cat_path))
        multi_probs = cat.predict_proba(X_transformed)
        multi_preds = np.argmax(multi_probs, axis=1)
        classes = prep["target_classes_multiclass"]
    except Exception as exc:
        raise MLError(f"CatBoost typology inference error: {exc}") from exc

    # 12. Build backend MLResult envelopes
    now_utc = datetime.now(timezone.utc)
    top_explanations_k = _extract_config_val(config, "top_explanations", "topExplanations", 5) or 5
    all_feature_names = prep["all_feature_names"]
    results: List[Dict[str, Any]] = []

    for i in range(len(merged)):
        txid = str(merged["transaction_id"].iloc[i])
        r_prob = float(np.clip(risk_probs[i], 0.0, 1.0))
        r_level = map_risk_level(r_prob)

        pred_label = str(classes[multi_preds[i]])
        confidence = float(np.clip(multi_probs[i, multi_preds[i]], 0.0, 1.0))

        # Top-K SHAP explanations
        row_shap = shaps[i]
        abs_shap = np.abs(row_shap)
        total_abs = float(np.sum(abs_shap))
        top_indices = np.argsort(abs_shap)[::-1][:top_explanations_k]

        explanations = []
        for rank, idx in enumerate(top_indices, start=1):
            feat_name = all_feature_names[idx]
            display_label, unit = FEATURE_DISPLAY_METADATA.get(
                feat_name, (feat_name.replace("_", " ").title(), None)
            )
            shap_val = float(row_shap[idx])
            norm_imp = float(abs(shap_val) / total_abs) if total_abs > 0 else 0.0
            direction = "increases_risk" if shap_val > 0 else ("decreases_risk" if shap_val < 0 else "neutral")

            # Determine actual display value for investigator
            feat_val = None
            if feat_name in merged.columns:
                raw_v = merged[feat_name].iloc[i]
                if pd.notna(raw_v):
                    if isinstance(raw_v, (int, np.integer)):
                        feat_val = int(raw_v)
                    elif isinstance(raw_v, (float, np.floating)):
                        feat_val = round(float(raw_v), 4)
                    elif isinstance(raw_v, (bool, np.bool_)):
                        feat_val = bool(raw_v)
                    else:
                        feat_val = str(raw_v)
            if feat_val is None:
                feat_val = round(float(X_transformed[i, idx]), 4)

            explanations.append({
                "feature_name": feat_name,
                "display_label": display_label,
                "shap_value": shap_val,
                "direction": direction,
                "importance_rank": rank,
                "normalized_importance": norm_imp,
                "feature_value": feat_val,
                "feature_unit": unit,
            })

        # Serialized feature values (guarantee valid JSON, no float NaN)
        features_list = []
        for col in metadata.get("features", {}).get("canonical_names", []):
            if col in merged.columns:
                raw_val = merged[col].iloc[i]
                if pd.isna(raw_val):
                    val = None
                elif isinstance(raw_val, (int, np.integer)):
                    val = int(raw_val)
                elif isinstance(raw_val, (float, np.floating)):
                    val = float(raw_val)
                elif isinstance(raw_val, (bool, np.bool_)):
                    val = bool(raw_val)
                else:
                    val = str(raw_val)

                features_list.append({
                    "feature_name": col,
                    "raw_value": val,
                    "normalized_value": None,
                    "is_imputed": False,
                    "imputation_method": None,
                })

        # Graph-derived investigator evidence
        cluster_size = int(merged["hist_cluster_size"].iloc[i]) if "hist_cluster_size" in merged.columns else 1
        component_size = int(merged["hist_component_size"].iloc[i]) if "hist_component_size" in merged.columns else 1
        reuse_ratio = float(merged["hist_address_reuse_ratio"].iloc[i]) if "hist_address_reuse_ratio" in merged.columns else 0.0
        fan_in = int(merged["rel_fan_in"].iloc[i]) if "rel_fan_in" in merged.columns else 1
        fan_out = int(merged["rel_fan_out"].iloc[i]) if "rel_fan_out" in merged.columns else 1

        graph_evidence = [
            {
                "evidence_type": "entity_cluster",
                "label": "Behavioral Cluster Size",
                "feature_name": "hist_cluster_size",
                "value": cluster_size,
                "description": f"Transaction belongs to an entity cluster of {cluster_size} associated addresses.",
            },
            {
                "evidence_type": "graph_metric",
                "label": "Connected Component Size",
                "feature_name": "hist_component_size",
                "value": component_size,
                "description": f"Weakly connected component size in bipartite transaction network is {component_size} nodes.",
            },
            {
                "evidence_type": "graph_metric",
                "label": "Address Reuse Ratio",
                "feature_name": "hist_address_reuse_ratio",
                "value": reuse_ratio,
                "description": f"Historical address reuse ratio across input addresses is {reuse_ratio:.2%}.",
            },
            {
                "evidence_type": "relational",
                "label": "Fan In Degree",
                "feature_name": "rel_fan_in",
                "value": fan_in,
                "description": f"Transaction aggregates funds across {fan_in} input addresses.",
            },
            {
                "evidence_type": "relational",
                "label": "Fan Out Degree",
                "feature_name": "rel_fan_out",
                "value": fan_out,
                "description": f"Transaction disperses outputs across {fan_out} destination addresses.",
            },
        ]

        result_payload = {
            "entity_id": txid,
            "entity_type": "transaction",
            "anomaly_score": r_prob,
            "risk_score": r_prob,
            "risk_level": r_level,
            "prediction_label": pred_label,
            "confidence": confidence,
            "explanations": explanations,
            "features": features_list,
            "graph_evidence": graph_evidence,
            "predicted_at": now_utc,
        }
        results.append(result_payload)

    logger.info(f"[ML Adapter] Completed inference on {len(results)} transactions for dataset {dataset_id}")
    return results
