"""Deterministic Alert Engine for AquaSynex.

Evaluates transaction ML results, temporal metrics, graph topology, and network telemetry
to generate grouped, deduplicated alerts into DuckDB with traceable evidence.
Conforms strictly to frozen CatBoost classes and existing persisted fields.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple
import duckdb
from backend.db.queries import alerts as alert_queries
from backend.utils.logging import logger

FROZEN_SUSPICIOUS_CATBOOST_CLASSES: Set[str] = {
    "peeling_chain",
    "mixing_like",
    "rapid_multihop",
    "coordinated_activity",
    "amount_anomaly",
}

ALL_FROZEN_CATBOOST_CLASSES: Set[str] = FROZEN_SUSPICIOUS_CATBOOST_CLASSES | {
    "normal",
    "benign_high_volume",
    "transaction_burst",
    "high_fan_in",
    "high_fan_out",
    "temporal_anomaly",
}


class AlertEngine:
    """Deterministic alert generator applying rules, grouping, and deduplication."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def generate_alerts_for_analysis(
        self,
        analysis_id: str,
        dataset_id: str,
    ) -> List[Dict[str, Any]]:
        """Evaluate ML results and telemetry for analysis_id and persist grouped alerts."""
        logger.info(f"[AlertEngine] Evaluating alerts for analysis {analysis_id} (dataset {dataset_id})...")

        # 1. Fetch ML results with feature and evidence JSON
        ml_rows = self.conn.execute(
            """
            SELECT entity_id, entity_type, risk_score, risk_level, prediction_label,
                   confidence, explanation_json, features_json, graph_evidence_json, predicted_at
            FROM ml_results
            WHERE analysis_id = ?
            ORDER BY risk_score DESC
            """,
            [analysis_id],
        ).fetchall()

        if not ml_rows:
            logger.info(f"[AlertEngine] No ML results found for analysis {analysis_id}")
            return []

        # 2. Fetch transaction timestamps and details
        tx_dict: Dict[str, Dict[str, Any]] = {}
        try:
            tx_rows = self.conn.execute(
                """
                SELECT transaction_id, timestamp, total_output_value_satoshi, fee_satoshi
                FROM transactions
                WHERE dataset_id = ?
                """,
                [dataset_id],
            ).fetchall()
            for r in tx_rows:
                tx_dict[r[0]] = {
                    "timestamp": r[1],
                    "output_sats": r[2],
                    "fee_sats": r[3],
                }
        except Exception as e:
            logger.warning(f"[AlertEngine] Could not fetch transaction details: {e}")

        # 3. Process each ML result and extract individual candidate alerts
        candidates: List[Dict[str, Any]] = []

        for row in ml_rows:
            txid = row[0]
            entity_type = row[1]
            risk_score = float(row[2])
            risk_level = str(row[3])
            pred_label = str(row[4]) if row[4] else "normal"
            confidence = float(row[5]) if row[5] is not None else 0.0

            # Parse features
            features_map: Dict[str, Any] = {}
            if row[7]:
                try:
                    parsed_feats = json.loads(row[7]) if isinstance(row[7], str) else row[7]
                    if isinstance(parsed_feats, list):
                        for f in parsed_feats:
                            if isinstance(f, dict):
                                features_map[f.get("feature_name")] = f.get("raw_value")
                    elif isinstance(parsed_feats, dict):
                        features_map.update(parsed_feats)
                except Exception:
                    pass

            # Parse graph evidence
            graph_evidence: List[Dict[str, Any]] = []
            if row[8]:
                try:
                    graph_evidence = json.loads(row[8]) if isinstance(row[8], str) else row[8]
                except Exception:
                    pass

            predicted_at = row[9] or datetime.now(timezone.utc)
            tx_info = tx_dict.get(txid, {})
            tx_timestamp = tx_info.get("timestamp") or predicted_at

            # Evaluate independent signal categories
            signals: List[Dict[str, Any]] = []

            # Signal A: XGBoost ML Risk
            if risk_score >= 0.50:
                signals.append({
                    "category": "ml_xgboost",
                    "reason": f"XGBoost risk score is {risk_score:.3f} (severity: {risk_level})",
                    "score": risk_score,
                })

            # Signal B: CatBoost Typology Anomaly
            if pred_label in FROZEN_SUSPICIOUS_CATBOOST_CLASSES and confidence >= 0.55:
                signals.append({
                    "category": "catboost_typology",
                    "reason": f"Classified as suspicious typology '{pred_label}' (confidence: {confidence:.1%})",
                    "behavior": pred_label,
                })

            # Signal C: Temporal Burst
            t_1m = features_map.get("time_txs_last_1m") or 0
            t_5m = features_map.get("time_txs_last_5m") or 0
            if t_1m >= 5 or t_5m >= 12 or pred_label == "transaction_burst":
                signals.append({
                    "category": "temporal_engine",
                    "reason": f"High temporal transaction velocity ({t_1m} tx/1m, {t_5m} tx/5m)",
                    "burst_count": max(t_1m, t_5m),
                })

            # Signal D: Graph Topological Anomaly
            comp_size = features_map.get("hist_component_size") or 0
            fan_in = features_map.get("rel_fan_in") or 0
            fan_out = features_map.get("rel_fan_out") or 0
            reuse_ratio = features_map.get("hist_address_reuse_ratio") or 0.0
            cluster_size = features_map.get("hist_cluster_size") or 1
            cluster_txs = features_map.get("hist_cluster_tx_count") or 1

            if comp_size >= 15 or fan_in >= 8 or fan_out >= 8 or reuse_ratio >= 0.75 or pred_label in ("high_fan_in", "high_fan_out"):
                signals.append({
                    "category": "graph_topology",
                    "reason": f"Graph metric anomaly (fan_in={fan_in}, fan_out={fan_out}, comp_size={comp_size}, reuse={reuse_ratio:.2f})",
                })

            # Signal E: Network Telemetry Anomaly (using only existing network fields)
            is_std_port = features_map.get("net_is_standard_bitcoin_port")
            src_port = features_map.get("net_src_port")
            dst_port = features_map.get("net_dst_port")
            is_non_std = (
                is_std_port in (False, 0)
                or (src_port is not None and src_port != 8333)
                or (dst_port is not None and dst_port != 8333)
            )
            if is_non_std:
                signals.append({
                    "category": "network_telemetry",
                    "reason": f"Broadcast via non-standard peer port (src: {src_port}, dst: {dst_port})",
                })

            # Signal F: Entity Cluster Activity
            if cluster_size >= 5 or cluster_txs >= 8:
                signals.append({
                    "category": "entity_cluster",
                    "reason": f"Belongs to a multi-address cluster ({cluster_size} addresses, {cluster_txs} transactions)",
                    "cluster_size": cluster_size,
                })

            if not signals:
                continue

            # Determine primary alert classification
            signal_categories = [s["category"] for s in signals]
            unique_categories = set(signal_categories)

            if len(unique_categories) >= 2:
                alert_type = "MULTI_SIGNAL"
                trigger_source = "composite"
                severity = "critical" if risk_score >= 0.67 else "high"
                priority = "P1"
                trigger_reason = f"Compound alert: {len(unique_categories)} independent signals ({', '.join(sorted(unique_categories))}) fired on transaction"
            elif "entity_cluster" in unique_categories:
                alert_type = "ENTITY_CLUSTER_ACTIVITY"
                trigger_source = "graph_topology"
                severity = "high"
                priority = "P2"
                trigger_reason = signals[0]["reason"]
            elif "catboost_typology" in unique_categories:
                alert_type = "BEHAVIOR_ANOMALY"
                trigger_source = "catboost_typology"
                severity = "high"
                priority = "P2"
                trigger_reason = signals[0]["reason"]
            elif "ml_xgboost" in unique_categories:
                alert_type = "HIGH_RISK_TRANSACTION"
                trigger_source = "ml_xgboost"
                severity = "critical" if risk_score >= 0.67 else "high"
                priority = "P1" if risk_score >= 0.85 else "P2"
                trigger_reason = signals[0]["reason"]
            elif "temporal_engine" in unique_categories:
                alert_type = "TEMPORAL_BURST"
                trigger_source = "temporal_engine"
                severity = "high" if risk_score >= 0.50 else "medium"
                priority = "P2" if risk_score >= 0.50 else "P3"
                trigger_reason = signals[0]["reason"]
            elif "graph_topology" in unique_categories:
                alert_type = "GRAPH_ANOMALY"
                trigger_source = "graph_topology"
                severity = "medium"
                priority = "P3"
                trigger_reason = signals[0]["reason"]
            else:
                alert_type = "NETWORK_ANOMALY"
                trigger_source = "network_telemetry"
                severity = "medium"
                priority = "P3"
                trigger_reason = signals[0]["reason"]

            # Determine grouping key
            # 1. Cluster grouping: if cluster size >= 3, group by cluster
            if cluster_size >= 3:
                grouping_key = f"cluster:{cluster_size}_{cluster_txs}"
            elif alert_type == "TEMPORAL_BURST":
                # Group by 5-minute bucket and behavior
                epoch_sec = int(tx_timestamp.timestamp()) if hasattr(tx_timestamp, "timestamp") else 0
                bucket_5m = (epoch_sec // 300) * 300
                grouping_key = f"burst:{bucket_5m}:{pred_label}"
            elif alert_type == "NETWORK_ANOMALY":
                country = features_map.get("net_country") or "UNKNOWN"
                asn = features_map.get("net_asn") or "UNKNOWN"
                grouping_key = f"net:{country}:{asn}"
            else:
                grouping_key = f"tx:{txid}"

            candidates.append({
                "txid": txid,
                "entity_type": entity_type,
                "risk_score": risk_score,
                "behavior_type": pred_label,
                "alert_type": alert_type,
                "severity": severity,
                "priority": priority,
                "trigger_source": trigger_source,
                "trigger_reason": trigger_reason,
                "grouping_key": grouping_key,
                "signals": signals,
                "signal_categories": list(unique_categories),
                "features_map": features_map,
                "graph_evidence": graph_evidence,
                "timestamp": tx_timestamp,
            })

        # 4. Group candidate alerts by (alert_type, grouping_key)
        groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for c in candidates:
            k = (c["alert_type"], c["grouping_key"])
            groups.setdefault(k, []).append(c)

        # 5. Build final deduplicated alert records
        persisted_alerts: List[Dict[str, Any]] = []

        for (alert_type, grouping_key), member_items in groups.items():
            # Sort member items by risk_score desc
            member_items.sort(key=lambda x: x["risk_score"], reverse=True)
            anchor = member_items[0]

            related_txids = list(dict.fromkeys(item["txid"] for item in member_items))
            max_risk = anchor["risk_score"]

            # Severity escalation: if 3+ critical transactions in group, elevate to critical / P1
            crit_count = sum(1 for item in member_items if item["risk_score"] >= 0.67)
            severity = "critical" if crit_count > 0 or max_risk >= 0.67 else anchor["severity"]
            priority = "P1" if severity == "critical" else anchor["priority"]

            # Collect distinct signal categories across all members
            all_signals: List[Dict[str, Any]] = []
            for item in member_items:
                all_signals.extend(item["signals"])

            # Compute stable fingerprint
            fingerprint_raw = f"{analysis_id}:{alert_type}:{grouping_key}"
            fingerprint = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()[:32]
            alert_id = f"alt-{fingerprint[:16]}"

            # Timestamps
            member_timestamps = [item["timestamp"] for item in member_items if item.get("timestamp")]
            first_seen_at = min(member_timestamps) if member_timestamps else datetime.now(timezone.utc)
            last_seen_at = max(member_timestamps) if member_timestamps else datetime.now(timezone.utc)

            # Metadata JSON storing full traceable evidence
            metadata_json = {
                "triggering_signals": list(set(s["category"] for s in all_signals)),
                "risk_score": max_risk,
                "behavior_type": anchor["behavior_type"],
                "source_features": {
                    k: v for k, v in anchor["features_map"].items()
                    if k in (
                        "time_txs_last_1m", "time_txs_last_5m", "time_txs_last_1h",
                        "hist_cluster_size", "hist_cluster_tx_count", "hist_component_size",
                        "hist_address_reuse_ratio", "rel_fan_in", "rel_fan_out",
                        "net_src_port", "net_dst_port", "net_is_standard_bitcoin_port",
                        "net_country", "net_asn", "tx_total_output_sats", "tx_fee_sats"
                    ) and v is not None
                },
                "graph_evidence": anchor["graph_evidence"],
                "related_txids": related_txids,
                "transaction_count": len(related_txids),
                "time_window": {
                    "first_seen": first_seen_at.isoformat() if hasattr(first_seen_at, "isoformat") else str(first_seen_at),
                    "last_seen": last_seen_at.isoformat() if hasattr(last_seen_at, "isoformat") else str(last_seen_at),
                },
            }

            reason_suffix = f" (aggregating {len(related_txids)} transactions)" if len(related_txids) > 1 else ""
            trigger_reason = f"{anchor['trigger_reason']}{reason_suffix}"

            alert_queries.insert_alert(
                conn=self.conn,
                alert_id=alert_id,
                analysis_id=analysis_id,
                dataset_id=dataset_id,
                fingerprint=fingerprint,
                grouping_key=grouping_key,
                transaction_id=anchor["txid"],
                entity_id=anchor["txid"] if len(related_txids) == 1 else f"cluster:{grouping_key}",
                entity_type="transaction" if len(related_txids) == 1 else "cluster",
                alert_type=alert_type,
                severity=severity,
                priority=priority,
                risk_score=max_risk,
                behavior_type=anchor["behavior_type"],
                trigger_source=anchor["trigger_source"],
                trigger_reason=trigger_reason,
                status="NEW",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                first_seen_at=first_seen_at,
                last_seen_at=last_seen_at,
                metadata_json=metadata_json,
            )

            persisted_alerts.append({
                "alert_id": alert_id,
                "alert_type": alert_type,
                "severity": severity,
                "priority": priority,
                "risk_score": max_risk,
                "status": "NEW",
                "transaction_count": len(related_txids),
            })

        logger.info(f"[AlertEngine] Successfully generated and persisted {len(persisted_alerts)} alerts for analysis {analysis_id}")
        return persisted_alerts
