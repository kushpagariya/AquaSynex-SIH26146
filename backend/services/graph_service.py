"""Graph analytics integration service and graph exporter.

Authoritative reference: docs/graph/graph-schema.md
Builds Cytoscape-compatible graph JSON from canonical transaction records and ML risk scores.
"""

from collections import deque
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import duckdb
from backend.db.queries import analyses as analysis_queries
from backend.utils.converters import satoshi_to_btc_str
from backend.utils.errors import AnalysisNotFoundError, GraphNotAvailableError
from backend.utils.logging import logger


def _safe_json_loads(val: Any) -> Any:
    if not val:
        return {}
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def _extract_metric_value(container: Any, keys: List[str]) -> Any:
    """Extract a metric value by candidate key names from either a dict or list of feature objects."""
    if not container:
        return None
    if isinstance(container, dict):
        for k in keys:
            if k in container:
                return container[k]
    elif isinstance(container, list):
        for item in container:
            if isinstance(item, dict):
                fname = item.get("featureName") or item.get("name") or item.get("feature") or item.get("key")
                if fname in keys:
                    return item.get("rawValue") if "rawValue" in item else item.get("value")
                for k in keys:
                    if k in item:
                        return item[k]
    return None


class GraphService:
    """Service providing graph export and neighborhood subgraph extraction."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def get_analysis_graph(
        self,
        analysis_id: str,
        min_risk_score: Optional[float] = None,
        max_nodes: int = 500,
        include_neighbors: bool = True,
    ) -> Dict[str, Any]:
        """Export transaction graph conforming to docs/graph/graph-schema.md."""
        analysis = analysis_queries.get_analysis_by_id(self.conn, analysis_id)
        dataset_id = analysis["dataset_id"]

        # Fetch address nodes with risk scores from ml_results
        node_query = """
        SELECT 
            a.address_id,
            a.transaction_count,
            a.total_received_satoshi,
            a.total_sent_satoshi,
            a.first_seen_timestamp,
            a.last_seen_timestamp,
            r.risk_score,
            r.risk_level
        FROM addresses a
        LEFT JOIN ml_results r 
            ON a.address_id = r.entity_id 
            AND a.dataset_id = r.dataset_id 
            AND r.analysis_id = ?
        WHERE a.dataset_id = ?
        """
        node_params = [analysis_id, dataset_id]
        if min_risk_score is not None:
            node_query += " AND r.risk_score >= ?"
            node_params.append(min_risk_score)

        node_query += " ORDER BY r.risk_score DESC NULLS LAST LIMIT ?"
        node_params.append(max_nodes)

        node_rel = self.conn.execute(node_query, node_params)
        node_rows = node_rel.fetchall()

        if not node_rows:
            # Check if dataset has any addresses
            addr_check = self.conn.execute(
                "SELECT COUNT(*) FROM addresses WHERE dataset_id = ?", [dataset_id]
            ).fetchone()
            if not addr_check or addr_check[0] == 0:
                raise GraphNotAvailableError("Graph is not available: no addresses found in dataset.")

        selected_address_ids = {r[0] for r in node_rows}
        nodes_dict: Dict[str, Dict[str, Any]] = {}

        for row in node_rows:
            addr_id, tx_cnt, recv_sat, sent_sat, first_seen, last_seen, r_score, r_lvl = row
            active_days = None
            if first_seen and last_seen:
                active_days = max(1, (last_seen - first_seen).days + 1)

            label = f"{addr_id[:8]}...{addr_id[-4:]}" if len(addr_id) > 12 else addr_id
            nodes_dict[addr_id] = {
                "id": addr_id,
                "label": label,
                "nodeType": "address",
                "riskScore": r_score,
                "riskLevel": r_lvl,
                "metadata": {
                    "transactionCount": tx_cnt,
                    "totalReceivedBtc": satoshi_to_btc_str(recv_sat),
                    "totalSentBtc": satoshi_to_btc_str(sent_sat),
                    "firstSeen": first_seen.isoformat() if first_seen else None,
                    "lastSeen": last_seen.isoformat() if last_seen else None,
                    "activeDays": active_days,
                },
            }

        # Query edges connecting addresses
        # An edge exists between input_address and output_address in the same transaction
        if not selected_address_ids:
            raw_edges = []
        else:
            selected_list = list(selected_address_ids)
            addr_placeholders = ", ".join("?" for _ in selected_list)
            edge_params = [dataset_id]

            if include_neighbors:
                edge_condition = f"AND (i.input_address IN ({addr_placeholders}) OR o.output_address IN ({addr_placeholders}))"
                edge_params.extend(selected_list)
                edge_params.extend(selected_list)
            else:
                edge_condition = f"AND i.input_address IN ({addr_placeholders}) AND o.output_address IN ({addr_placeholders})"
                edge_params.extend(selected_list)
                edge_params.extend(selected_list)

            edge_query = f"""
            SELECT 
                i.input_address AS source,
                o.output_address AS target,
                t.transaction_id,
                o.output_value_satoshi AS value_satoshi,
                t.timestamp
            FROM (
                SELECT DISTINCT transaction_id, dataset_id, input_address
                FROM transaction_inputs
                WHERE input_address IS NOT NULL
            ) i
            JOIN (
                SELECT transaction_id, dataset_id, output_address, SUM(output_value_satoshi) AS output_value_satoshi
                FROM transaction_outputs
                WHERE output_address IS NOT NULL
                GROUP BY transaction_id, dataset_id, output_address
            ) o ON i.transaction_id = o.transaction_id AND i.dataset_id = o.dataset_id
            JOIN transactions t ON i.transaction_id = t.transaction_id AND i.dataset_id = t.dataset_id
            WHERE i.dataset_id = ?
              AND i.input_address != o.output_address
              {edge_condition}
            """
            edge_rel = self.conn.execute(edge_query, edge_params)
            raw_edges = edge_rel.fetchall()

        # Aggregate raw transactions into directed edges
        edges_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for src, tgt, tx_id, val_sat, ts in raw_edges:
            # Include neighbor nodes if configured
            if include_neighbors:
                if src not in nodes_dict:
                    src_label = f"{src[:8]}...{src[-4:]}" if len(src) > 12 else src
                    nodes_dict[src] = {
                        "id": src,
                        "label": src_label,
                        "nodeType": "address",
                        "riskScore": None,
                        "riskLevel": None,
                        "metadata": {},
                    }
                if tgt not in nodes_dict:
                    tgt_label = f"{tgt[:8]}...{tgt[-4:]}" if len(tgt) > 12 else tgt
                    nodes_dict[tgt] = {
                        "id": tgt,
                        "label": tgt_label,
                        "nodeType": "address",
                        "riskScore": None,
                        "riskLevel": None,
                        "metadata": {},
                    }

            key = (src, tgt)
            if key not in edges_map:
                edges_map[key] = {
                    "id": f"{src}→{tgt}",
                    "source": src,
                    "target": tgt,
                    "edgeType": "transaction",
                    "transactions": [],
                    "totalValueSatoshi": 0,
                    "transactionCount": 0,
                }

            val_sat = val_sat or 0
            edges_map[key]["totalValueSatoshi"] += val_sat
            edges_map[key]["transactionCount"] += 1
            edges_map[key]["transactions"].append({
                "transactionId": tx_id,
                "valueSatoshi": val_sat,
                "valueBtc": satoshi_to_btc_str(val_sat),
                "timestamp": ts.isoformat() if ts else None,
            })

        # Apply max_nodes limit after neighbor expansion
        if len(nodes_dict) > max_nodes:
            kept_nodes = set(list(selected_address_ids)[:max_nodes])
            for k in nodes_dict:
                if len(kept_nodes) >= max_nodes:
                    break
                kept_nodes.add(k)
            nodes_dict = {k: nodes_dict[k] for k in kept_nodes}
            edges_map = {k: v for k, v in edges_map.items() if k[0] in kept_nodes and k[1] in kept_nodes}

        edges_list = []
        for edge_data in edges_map.values():
            edge_data["totalValueBtc"] = satoshi_to_btc_str(edge_data["totalValueSatoshi"])
            edges_list.append(edge_data)

        nodes_list = list(nodes_dict.values())
        return {
            "graphId": str(uuid.uuid4()),
            "analysisId": analysis_id,
            "datasetId": dataset_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "nodeCount": len(nodes_list),
            "edgeCount": len(edges_list),
            "isSubgraph": False,
            "subgraphCenter": None,
            "nodes": nodes_list,
            "edges": edges_list,
        }

    def get_address_subgraph(
        self,
        address_id: str,
        hops: int = 2,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract N-hop neighborhood subgraph centered around a specific address."""
        hops = min(max(1, hops), 3)  # limit hops between 1 and 3

        dataset_id = None
        if analysis_id:
            analysis = analysis_queries.get_analysis_by_id(self.conn, analysis_id)
            dataset_id = analysis.get("dataset_id")

        if dataset_id:
            # Verify address exists in this dataset
            addr_row = self.conn.execute(
                "SELECT 1 FROM addresses WHERE address_id = ? AND dataset_id = ? "
                "UNION ALL SELECT 1 FROM transaction_inputs WHERE input_address = ? AND dataset_id = ? "
                "UNION ALL SELECT 1 FROM transaction_outputs WHERE output_address = ? AND dataset_id = ? LIMIT 1",
                [address_id, dataset_id, address_id, dataset_id, address_id, dataset_id],
            ).fetchone()
            if not addr_row:
                # Fallback: check if address_id is actually a transaction_id
                tx_row = self.conn.execute(
                    "SELECT 1 FROM transactions WHERE transaction_id = ? AND dataset_id = ?",
                    [address_id, dataset_id],
                ).fetchone()
                if tx_row:
                    hood = self.get_neighborhood(entity_id=address_id, analysis_id=analysis_id, dataset_id=dataset_id, depth=hops)
                    return {
                        "graphId": hood["graphId"],
                        "analysisId": hood.get("analysisId"),
                        "datasetId": hood["datasetId"],
                        "generatedAt": hood["generatedAt"],
                        "nodeCount": hood.get("nodeCount") or len(hood["nodes"]),
                        "edgeCount": hood.get("edgeCount") or len(hood["edges"]),
                        "isSubgraph": True,
                        "subgraphCenter": address_id,
                        "nodes": hood["nodes"],
                        "edges": hood["edges"],
                    }
                raise GraphNotAvailableError(
                    f"Address '{address_id}' not found in dataset '{dataset_id}' for analysis '{analysis_id}'."
                )
        else:
            # Find which dataset contains this address
            addr_row = self.conn.execute(
                "SELECT dataset_id FROM addresses WHERE address_id = ? LIMIT 1", [address_id]
            ).fetchone()
            dataset_id = addr_row[0] if addr_row else None

            if not dataset_id:
                in_row = self.conn.execute(
                    "SELECT dataset_id FROM transaction_inputs WHERE input_address = ? LIMIT 1", [address_id]
                ).fetchone()
                dataset_id = in_row[0] if in_row else None

            if not dataset_id:
                out_row = self.conn.execute(
                    "SELECT dataset_id FROM transaction_outputs WHERE output_address = ? LIMIT 1", [address_id]
                ).fetchone()
                dataset_id = out_row[0] if out_row else None

            if not dataset_id:
                # Fallback: check if address_id is actually a transaction_id across datasets
                tx_row = self.conn.execute(
                    "SELECT dataset_id FROM transactions WHERE transaction_id = ? LIMIT 1", [address_id]
                ).fetchone()
                if tx_row:
                    dataset_id = tx_row[0]
                    hood = self.get_neighborhood(entity_id=address_id, analysis_id=analysis_id, dataset_id=dataset_id, depth=hops)
                    return {
                        "graphId": hood["graphId"],
                        "analysisId": hood.get("analysisId"),
                        "datasetId": hood["datasetId"],
                        "generatedAt": hood["generatedAt"],
                        "nodeCount": hood.get("nodeCount") or len(hood["nodes"]),
                        "edgeCount": hood.get("edgeCount") or len(hood["edges"]),
                        "isSubgraph": True,
                        "subgraphCenter": address_id,
                        "nodes": hood["nodes"],
                        "edges": hood["edges"],
                    }
                raise GraphNotAvailableError(f"Address '{address_id}' not found in any dataset.")

        # Batch breadth-first search for N-hop neighbors
        visited_nodes: Set[str] = {address_id}
        current_frontier: Set[str] = {address_id}

        for _ in range(hops):
            if not current_frontier or len(visited_nodes) >= 500:
                break

            frontier_list = list(current_frontier)
            frontier_placeholders = ", ".join("?" for _ in frontier_list)

            # Batch query next hop neighbors (forward and backward)
            fwd_sql = f"""
            SELECT DISTINCT o.output_address
            FROM transaction_inputs i
            JOIN transaction_outputs o ON i.transaction_id = o.transaction_id AND i.dataset_id = o.dataset_id
            WHERE i.dataset_id = ? AND i.input_address IN ({frontier_placeholders}) 
              AND o.output_address IS NOT NULL
            LIMIT 100
            """
            bwd_sql = f"""
            SELECT DISTINCT i.input_address
            FROM transaction_outputs o
            JOIN transaction_inputs i ON o.transaction_id = i.transaction_id AND o.dataset_id = i.dataset_id
            WHERE o.dataset_id = ? AND o.output_address IN ({frontier_placeholders}) 
              AND i.input_address IS NOT NULL
            LIMIT 100
            """
            fwd_rows = self.conn.execute(fwd_sql, [dataset_id] + frontier_list).fetchall()
            bwd_rows = self.conn.execute(bwd_sql, [dataset_id] + frontier_list).fetchall()

            next_frontier: Set[str] = set()
            for (nbr,) in fwd_rows:
                if len(visited_nodes) >= 500:
                    break
                if nbr not in visited_nodes:
                    visited_nodes.add(nbr)
                    next_frontier.add(nbr)
            for (nbr,) in bwd_rows:
                if len(visited_nodes) >= 500:
                    break
                if nbr not in visited_nodes:
                    visited_nodes.add(nbr)
                    next_frontier.add(nbr)

            current_frontier = next_frontier

        # Retrieve nodes detail in a single batch query
        visited_list = list(visited_nodes)
        visited_placeholders = ", ".join("?" for _ in visited_list)
        if analysis_id:
            node_sql = f"""
            SELECT a.address_id, a.transaction_count, a.total_received_satoshi, a.total_sent_satoshi,
                   a.first_seen_timestamp, a.last_seen_timestamp,
                   r.risk_score, r.risk_level
            FROM addresses a
            LEFT JOIN ml_results r ON a.address_id = r.entity_id AND a.dataset_id = r.dataset_id AND r.analysis_id = ?
            WHERE a.address_id IN ({visited_placeholders}) AND a.dataset_id = ?
            """
            node_params = [analysis_id] + visited_list + [dataset_id]
        else:
            node_sql = f"""
            SELECT a.address_id, a.transaction_count, a.total_received_satoshi, a.total_sent_satoshi,
                   a.first_seen_timestamp, a.last_seen_timestamp,
                   r.risk_score, r.risk_level
            FROM addresses a
            LEFT JOIN (
                SELECT entity_id, dataset_id, risk_score, risk_level
                FROM (
                    SELECT entity_id, dataset_id, risk_score, risk_level,
                           ROW_NUMBER() OVER (PARTITION BY entity_id, dataset_id ORDER BY predicted_at DESC NULLS LAST, result_id DESC) as rn
                    FROM ml_results
                    WHERE entity_type = 'address'
                ) sub WHERE rn = 1
            ) r ON a.address_id = r.entity_id AND a.dataset_id = r.dataset_id
            WHERE a.address_id IN ({visited_placeholders}) AND a.dataset_id = ?
            """
            node_params = visited_list + [dataset_id]

        node_rel = self.conn.execute(node_sql, node_params)
        fetched_nodes = {row[0]: row for row in node_rel.fetchall()}

        nodes_dict: Dict[str, Dict[str, Any]] = {}
        for addr in visited_nodes:
            row = fetched_nodes.get(addr)
            if row:
                _, tx_cnt, recv_sat, sent_sat, first_seen, last_seen, r_score, r_lvl = row
            else:
                tx_cnt, recv_sat, sent_sat, first_seen, last_seen, r_score, r_lvl = (0, 0, 0, None, None, None, None)

            active_days = max(1, (last_seen - first_seen).days + 1) if (first_seen and last_seen) else None
            label = f"{addr[:8]}...{addr[-4:]}" if len(addr) > 12 else addr

            nodes_dict[addr] = {
                "id": addr,
                "label": label,
                "nodeType": "address",
                "riskScore": r_score,
                "riskLevel": r_lvl,
                "metadata": {
                    "transactionCount": tx_cnt,
                    "totalReceivedBtc": satoshi_to_btc_str(recv_sat),
                    "totalSentBtc": satoshi_to_btc_str(sent_sat),
                    "firstSeen": first_seen.isoformat() if first_seen else None,
                    "lastSeen": last_seen.isoformat() if last_seen else None,
                    "activeDays": active_days,
                },
            }

        # Query edges between visited nodes
        edge_placeholders = ", ".join("?" for _ in visited_list)
        edge_query = f"""
        SELECT 
            i.input_address AS source,
            o.output_address AS target,
            t.transaction_id,
            o.output_value_satoshi AS value_satoshi,
            t.timestamp
        FROM (
            SELECT DISTINCT transaction_id, dataset_id, input_address
            FROM transaction_inputs
            WHERE input_address IS NOT NULL
        ) i
        JOIN (
            SELECT transaction_id, dataset_id, output_address, SUM(output_value_satoshi) AS output_value_satoshi
            FROM transaction_outputs
            WHERE output_address IS NOT NULL
            GROUP BY transaction_id, dataset_id, output_address
        ) o ON i.transaction_id = o.transaction_id AND i.dataset_id = o.dataset_id
        JOIN transactions t ON i.transaction_id = t.transaction_id AND i.dataset_id = t.dataset_id
        WHERE i.dataset_id = ?
          AND i.input_address IN ({edge_placeholders})
          AND o.output_address IN ({edge_placeholders})
          AND i.input_address != o.output_address
        """
        edge_params = [dataset_id] + visited_list + visited_list
        edge_rel = self.conn.execute(edge_query, edge_params)

        edges_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for src, tgt, tx_id, val_sat, ts in edge_rel.fetchall():
            key = (src, tgt)
            if key not in edges_map:
                edges_map[key] = {
                    "id": f"{src}→{tgt}",
                    "source": src,
                    "target": tgt,
                    "edgeType": "transaction",
                    "transactions": [],
                    "totalValueSatoshi": 0,
                    "transactionCount": 0,
                }
            val_sat = val_sat or 0
            edges_map[key]["totalValueSatoshi"] += val_sat
            edges_map[key]["transactionCount"] += 1
            edges_map[key]["transactions"].append({
                "transactionId": tx_id,
                "valueSatoshi": val_sat,
                "valueBtc": satoshi_to_btc_str(val_sat),
                "timestamp": ts.isoformat() if ts else None,
            })

        edges_list = []
        for edge_data in edges_map.values():
            edge_data["totalValueBtc"] = satoshi_to_btc_str(edge_data["totalValueSatoshi"])
            edges_list.append(edge_data)

        return {
            "graphId": str(uuid.uuid4()),
            "analysisId": analysis_id,
            "datasetId": dataset_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "nodeCount": len(nodes_dict),
            "edgeCount": len(edges_list),
            "isSubgraph": True,
            "subgraphCenter": address_id,
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
        }

    def get_neighborhood(
        self,
        entity_id: str,
        analysis_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        depth: int = 2,
        high_risk_only: bool = False,
    ) -> Dict[str, Any]:
        """Extract multi-hop bipartite neighborhood subgraph around a transaction or address.
        
        Supports directed bipartite graph: Address -> Transaction -> Address.
        Provides authoritative entity type resolution, ML risk evidence, network events, and alerts.
        """
        entity_id = entity_id.strip()
        depth = min(max(1, depth), 3)

        # 1. Resolve analysis and dataset context
        if analysis_id:
            analysis = analysis_queries.get_analysis_by_id(self.conn, analysis_id)
            dataset_id = analysis["dataset_id"]
        elif dataset_id:
            a_row = self.conn.execute(
                "SELECT analysis_id FROM analysis_runs WHERE dataset_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1",
                [dataset_id],
            ).fetchone()
            if a_row:
                analysis_id = a_row[0]
        else:
            # Auto-discover dataset_id by checking entity_id across datasets
            t_row = self.conn.execute(
                "SELECT dataset_id FROM transactions WHERE transaction_id = ? LIMIT 1", [entity_id]
            ).fetchone()
            if t_row:
                dataset_id = t_row[0]
            else:
                addr_row = self.conn.execute(
                    "SELECT dataset_id FROM addresses WHERE address_id = ? "
                    "UNION ALL SELECT dataset_id FROM transaction_inputs WHERE input_address = ? "
                    "UNION ALL SELECT dataset_id FROM transaction_outputs WHERE output_address = ? LIMIT 1",
                    [entity_id, entity_id, entity_id],
                ).fetchone()
                if addr_row:
                    dataset_id = addr_row[0]

            if dataset_id:
                a_row = self.conn.execute(
                    "SELECT analysis_id FROM analysis_runs WHERE dataset_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1",
                    [dataset_id],
                ).fetchone()
                if a_row:
                    analysis_id = a_row[0]
            else:
                is_hex64 = len(entity_id) == 64 and all(c in "0123456789abcdefABCDEF" for c in entity_id)
                if is_hex64:
                    raise GraphNotAvailableError(f"Transaction TXID '{entity_id}' not found in any dataset.")
                else:
                    raise GraphNotAvailableError(f"Address '{entity_id}' not found in any dataset.")

        # 2. Authoritative Entity Type Resolution
        req_type = entity_type.lower().strip() if entity_type else None
        if req_type in ("tx", "txid", "transaction"):
            resolved_type = "transaction"
            tx_check = self.conn.execute(
                "SELECT 1 FROM transactions WHERE transaction_id = ? AND dataset_id = ?",
                [entity_id, dataset_id],
            ).fetchone()
            if not tx_check:
                other_ds = self.conn.execute(
                    "SELECT dataset_id FROM transactions WHERE transaction_id = ? LIMIT 1",
                    [entity_id],
                ).fetchone()
                if other_ds:
                    raise GraphNotAvailableError(
                        f"Transaction TXID '{entity_id}' not found in the selected analysis (it belongs to dataset '{other_ds[0]}')."
                    )
                raise GraphNotAvailableError(f"Transaction TXID '{entity_id}' not found in the selected analysis.")
        elif req_type in ("addr", "wallet", "address"):
            resolved_type = "address"
            addr_check = self.conn.execute(
                "SELECT 1 FROM addresses WHERE address_id = ? AND dataset_id = ? "
                "UNION ALL SELECT 1 FROM transaction_inputs WHERE input_address = ? AND dataset_id = ? "
                "UNION ALL SELECT 1 FROM transaction_outputs WHERE output_address = ? AND dataset_id = ? LIMIT 1",
                [entity_id, dataset_id, entity_id, dataset_id, entity_id, dataset_id],
            ).fetchone()
            if not addr_check:
                other_ds = self.conn.execute(
                    "SELECT dataset_id FROM addresses WHERE address_id = ? "
                    "UNION ALL SELECT dataset_id FROM transaction_inputs WHERE input_address = ? "
                    "UNION ALL SELECT dataset_id FROM transaction_outputs WHERE output_address = ? LIMIT 1",
                    [entity_id, entity_id, entity_id],
                ).fetchone()
                if other_ds:
                    raise GraphNotAvailableError(
                        f"Address '{entity_id}' not found in the selected analysis (it belongs to dataset '{other_ds[0]}')."
                    )
                raise GraphNotAvailableError(f"Address '{entity_id}' not found in the selected analysis.")
        else:
            # Auto-detect entity type
            is_tx = self.conn.execute(
                "SELECT 1 FROM transactions WHERE transaction_id = ? AND dataset_id = ?",
                [entity_id, dataset_id],
            ).fetchone()
            if is_tx:
                resolved_type = "transaction"
            else:
                is_addr = self.conn.execute(
                    "SELECT 1 FROM addresses WHERE address_id = ? AND dataset_id = ? "
                    "UNION ALL SELECT 1 FROM transaction_inputs WHERE input_address = ? AND dataset_id = ? "
                    "UNION ALL SELECT 1 FROM transaction_outputs WHERE output_address = ? AND dataset_id = ? LIMIT 1",
                    [entity_id, dataset_id, entity_id, dataset_id, entity_id, dataset_id],
                ).fetchone()
                if is_addr:
                    resolved_type = "address"
                else:
                    other_tx = self.conn.execute(
                        "SELECT dataset_id FROM transactions WHERE transaction_id = ? LIMIT 1",
                        [entity_id],
                    ).fetchone()
                    if other_tx:
                        raise GraphNotAvailableError(
                            f"Transaction TXID '{entity_id}' not found in the selected analysis (it belongs to dataset '{other_tx[0]}')."
                        )
                    other_addr = self.conn.execute(
                        "SELECT dataset_id FROM addresses WHERE address_id = ? "
                        "UNION ALL SELECT dataset_id FROM transaction_inputs WHERE input_address = ? "
                        "UNION ALL SELECT dataset_id FROM transaction_outputs WHERE output_address = ? LIMIT 1",
                        [entity_id, entity_id, entity_id],
                    ).fetchone()
                    if other_addr:
                        raise GraphNotAvailableError(
                            f"Address '{entity_id}' not found in the selected analysis (it belongs to dataset '{other_addr[0]}')."
                        )
                    is_hex64 = len(entity_id) == 64 and all(c in "0123456789abcdefABCDEF" for c in entity_id)
                    if is_hex64:
                        raise GraphNotAvailableError(f"Transaction TXID '{entity_id}' not found in the selected analysis.")
                    else:
                        raise GraphNotAvailableError(f"Address '{entity_id}' not found in the selected analysis.")

        # 3. Bipartite BFS Neighborhood Traversal
        visited_txs: Set[str] = set()
        visited_addrs: Set[str] = set()

        if resolved_type == "transaction":
            visited_txs.add(entity_id)
            frontier_txs: Set[str] = {entity_id}
            frontier_addrs: Set[str] = set()

            # Hop 1: TX -> connected input and output addresses
            in_rows = self.conn.execute(
                "SELECT DISTINCT input_address FROM transaction_inputs WHERE transaction_id = ? AND dataset_id = ? AND input_address IS NOT NULL",
                [entity_id, dataset_id],
            ).fetchall()
            out_rows = self.conn.execute(
                "SELECT DISTINCT output_address FROM transaction_outputs WHERE transaction_id = ? AND dataset_id = ? AND output_address IS NOT NULL",
                [entity_id, dataset_id],
            ).fetchall()
            hop1_addrs = {r[0] for r in in_rows + out_rows if r[0]}
            if not hop1_addrs:
                raise GraphNotAvailableError("Entity found, but no connected graph records were found.")
            visited_addrs.update(hop1_addrs)
            frontier_addrs = set(hop1_addrs)

            # Hop 2 (if depth >= 2): addresses -> connected transactions
            if depth >= 2 and frontier_addrs:
                f_list = list(frontier_addrs)[:50]
                ph = ", ".join("?" for _ in f_list)
                tx_rows = self.conn.execute(
                    f"SELECT DISTINCT transaction_id FROM transaction_inputs WHERE input_address IN ({ph}) AND dataset_id = ? "
                    f"UNION SELECT DISTINCT transaction_id FROM transaction_outputs WHERE output_address IN ({ph}) AND dataset_id = ? LIMIT 60",
                    f_list + [dataset_id] + f_list + [dataset_id],
                ).fetchall()
                hop2_txs = {r[0] for r in tx_rows if r[0] not in visited_txs}
                visited_txs.update(hop2_txs)
                frontier_txs = hop2_txs

            # Hop 3 (if depth >= 3): transactions -> connected addresses
            if depth >= 3 and frontier_txs:
                f_list = list(frontier_txs)[:40]
                ph = ", ".join("?" for _ in f_list)
                addr_rows = self.conn.execute(
                    f"SELECT DISTINCT input_address FROM transaction_inputs WHERE transaction_id IN ({ph}) AND dataset_id = ? AND input_address IS NOT NULL "
                    f"UNION SELECT DISTINCT output_address FROM transaction_outputs WHERE transaction_id IN ({ph}) AND dataset_id = ? AND output_address IS NOT NULL LIMIT 80",
                    f_list + [dataset_id] + f_list + [dataset_id],
                ).fetchall()
                hop3_addrs = {r[0] for r in addr_rows if r[0] not in visited_addrs}
                visited_addrs.update(hop3_addrs)

        else:
            # resolved_type == "address"
            visited_addrs.add(entity_id)

            # Hop 1: Address -> connected transactions
            tx_rows = self.conn.execute(
                "SELECT DISTINCT transaction_id FROM transaction_inputs WHERE input_address = ? AND dataset_id = ? "
                "UNION SELECT DISTINCT transaction_id FROM transaction_outputs WHERE output_address = ? AND dataset_id = ? LIMIT 50",
                [entity_id, dataset_id, entity_id, dataset_id],
            ).fetchall()
            hop1_txs = {r[0] for r in tx_rows if r[0]}
            if not hop1_txs:
                raise GraphNotAvailableError("Entity found, but no connected graph records were found.")
            visited_txs.update(hop1_txs)
            frontier_txs = set(hop1_txs)

            # Hop 2 (if depth >= 2): transactions -> connected addresses
            if depth >= 2 and frontier_txs:
                f_list = list(frontier_txs)[:40]
                ph = ", ".join("?" for _ in f_list)
                addr_rows = self.conn.execute(
                    f"SELECT DISTINCT input_address FROM transaction_inputs WHERE transaction_id IN ({ph}) AND dataset_id = ? AND input_address IS NOT NULL "
                    f"UNION SELECT DISTINCT output_address FROM transaction_outputs WHERE transaction_id IN ({ph}) AND dataset_id = ? AND output_address IS NOT NULL LIMIT 80",
                    f_list + [dataset_id] + f_list + [dataset_id],
                ).fetchall()
                hop2_addrs = {r[0] for r in addr_rows if r[0] not in visited_addrs}
                visited_addrs.update(hop2_addrs)
                frontier_addrs = hop2_addrs

            # Hop 3 (if depth >= 3): addresses -> connected transactions
            if depth >= 3 and frontier_addrs:
                f_list = list(frontier_addrs)[:50]
                ph = ", ".join("?" for _ in f_list)
                tx_rows = self.conn.execute(
                    f"SELECT DISTINCT transaction_id FROM transaction_inputs WHERE input_address IN ({ph}) AND dataset_id = ? "
                    f"UNION SELECT DISTINCT transaction_id FROM transaction_outputs WHERE output_address IN ({ph}) AND dataset_id = ? LIMIT 60",
                    f_list + [dataset_id] + f_list + [dataset_id],
                ).fetchall()
                hop3_txs = {r[0] for r in tx_rows if r[0] not in visited_txs}
                visited_txs.update(hop3_txs)

        # 4. Fetch Node Details & Metadata
        tx_dict: Dict[str, Dict[str, Any]] = {}
        if visited_txs:
            tx_list = list(visited_txs)
            ph = ", ".join("?" for _ in tx_list)
            tx_rows = self.conn.execute(
                f"SELECT transaction_id, block_hash, block_height, timestamp, "
                f"       input_count, output_count, total_input_value_satoshi, "
                f"       total_output_value_satoshi, fee_satoshi, transaction_size_bytes "
                f"FROM transactions WHERE dataset_id = ? AND transaction_id IN ({ph})",
                [dataset_id] + tx_list,
            ).fetchall()
            for r in tx_rows:
                tid, b_hash, b_height, ts, in_cnt, out_cnt, in_sat, out_sat, fee_sat, sz_bytes = r
                fee_sat = fee_sat or 0
                sz_bytes = sz_bytes or 0
                fee_rate = round(fee_sat / sz_bytes, 2) if sz_bytes > 0 else None
                tx_dict[tid] = {
                    "id": tid,
                    "label": f"{tid[:8]}...{tid[-6:]}" if len(tid) > 14 else tid,
                    "nodeType": "transaction",
                    "riskScore": None,
                    "riskLevel": None,
                    "behaviorType": None,
                    "metadata": {
                        "transactionId": tid,
                        "timestamp": ts.isoformat() if ts else None,
                        "amountBtc": satoshi_to_btc_str(out_sat or in_sat or 0),
                        "totalOutputValueBtc": satoshi_to_btc_str(out_sat or 0),
                        "totalInputValueBtc": satoshi_to_btc_str(in_sat or 0),
                        "feeBtc": satoshi_to_btc_str(fee_sat),
                        "feeSatoshi": fee_sat,
                        "feeRate": fee_rate,
                        "inputCount": in_cnt,
                        "outputCount": out_cnt,
                        "blockHeight": b_height,
                        "behavior": None,
                        "riskScore": None,
                        "riskLevel": None,
                        "evidence": {
                            "graph": {"fanIn": in_cnt, "fanOut": out_cnt},
                            "temporal": {},
                            "network": {},
                            "ml": {},
                        },
                    },
                }

            if analysis_id:
                ml_query = (
                    f"SELECT entity_id, anomaly_score, risk_score, risk_level, "
                    f"       prediction_label, confidence, explanation_json, "
                    f"       features_json, graph_evidence_json, model_id "
                    f"FROM ml_results WHERE dataset_id = ? AND analysis_id = ? "
                    f"  AND entity_type = 'transaction' AND entity_id IN ({ph})"
                )
                ml_params = [dataset_id, analysis_id] + tx_list
            else:
                ml_query = (
                    f"SELECT entity_id, anomaly_score, risk_score, risk_level, "
                    f"       prediction_label, confidence, explanation_json, "
                    f"       features_json, graph_evidence_json, model_id "
                    f"FROM ml_results WHERE dataset_id = ? "
                    f"  AND entity_type = 'transaction' AND entity_id IN ({ph})"
                )
                ml_params = [dataset_id] + tx_list

            ml_rows = self.conn.execute(ml_query, ml_params).fetchall()
            for r in ml_rows:
                eid, anom, r_score, r_lvl, pred_lbl, conf, exp_json, feat_json, gr_ev_json, m_id = r
                if eid in tx_dict:
                    features = _safe_json_loads(feat_json)
                    explanation = _safe_json_loads(exp_json)
                    graph_ev = _safe_json_loads(gr_ev_json)

                    tx_dict[eid]["riskScore"] = r_score
                    tx_dict[eid]["riskLevel"] = r_lvl.lower() if r_lvl else None
                    tx_dict[eid]["behaviorType"] = pred_lbl
                    m = tx_dict[eid]["metadata"]
                    m["riskScore"] = r_score
                    m["riskLevel"] = r_lvl.lower() if r_lvl else None
                    m["behavior"] = pred_lbl

                    m["evidence"]["graph"]["componentSize"] = _extract_metric_value(features, ["component_size", "componentSize"]) or _extract_metric_value(graph_ev, ["component_size", "componentSize"])
                    m["evidence"]["graph"]["addressReuse"] = _extract_metric_value(features, ["address_reuse", "addressReuse"]) or _extract_metric_value(graph_ev, ["address_reuse", "addressReuse"])
                    m["evidence"]["graph"]["clusterId"] = _extract_metric_value(features, ["cluster_id", "clusterId"]) or _extract_metric_value(graph_ev, ["cluster_id", "clusterId"])

                    m["evidence"]["temporal"]["txInLast1m"] = _extract_metric_value(features, ["tx_in_last_1m", "tx_count_1m", "txInLast1m"])
                    m["evidence"]["temporal"]["txInLast5m"] = _extract_metric_value(features, ["tx_in_last_5m", "tx_count_5m", "txInLast5m"])
                    m["evidence"]["temporal"]["timeSincePrevTx"] = _extract_metric_value(features, ["time_since_prev_tx", "time_diff_sec", "timeSincePrevTx"])

                    m["evidence"]["ml"]["riskScore"] = r_score
                    m["evidence"]["ml"]["riskLevel"] = r_lvl
                    m["evidence"]["ml"]["behaviorClassification"] = pred_lbl
                    m["evidence"]["ml"]["confidence"] = conf
                    m["evidence"]["ml"]["modelId"] = m_id
                    if isinstance(explanation, dict) and "top_features" in explanation:
                        m["evidence"]["ml"]["topFeatures"] = explanation["top_features"]
                    elif isinstance(explanation, list) and len(explanation) > 0:
                        m["evidence"]["ml"]["topFeatures"] = explanation

            net_rows = self.conn.execute(
                f"SELECT transaction_id, src_ip, src_port, dst_ip, dst_port, country, asn "
                f"FROM network_events WHERE dataset_id = ? AND transaction_id IN ({ph})",
                [dataset_id] + tx_list,
            ).fetchall()
            for r in net_rows:
                tid, s_ip, s_port, d_ip, d_port, country, asn = r
                if tid in tx_dict:
                    tx_dict[tid]["metadata"]["evidence"]["network"] = {
                        "country": country,
                        "asn": asn,
                        "srcIp": s_ip,
                        "srcPort": s_port,
                        "dstPort": d_port,
                    }

        addr_dict: Dict[str, Dict[str, Any]] = {}
        if visited_addrs:
            addr_list = list(visited_addrs)
            ph = ", ".join("?" for _ in addr_list)
            addr_rows = self.conn.execute(
                f"SELECT address_id, address_type, first_seen_timestamp, last_seen_timestamp, "
                f"       total_received_satoshi, total_sent_satoshi, transaction_count "
                f"FROM addresses WHERE dataset_id = ? AND address_id IN ({ph})",
                [dataset_id] + addr_list,
            ).fetchall()
            for r in addr_rows:
                aid, a_type, f_seen, l_seen, recv_sat, sent_sat, tx_cnt = r
                recv_sat = recv_sat or 0
                sent_sat = sent_sat or 0
                act_days = max(1, (l_seen - f_seen).days + 1) if (f_seen and l_seen) else None
                addr_dict[aid] = {
                    "id": aid,
                    "label": f"{aid[:8]}...{aid[-4:]}" if len(aid) > 12 else aid,
                    "nodeType": "address",
                    "riskScore": None,
                    "riskLevel": None,
                    "behaviorType": None,
                    "metadata": {
                        "address": aid,
                        "addressType": a_type or "standard",
                        "transactionCount": tx_cnt or 0,
                        "incomingActivityBtc": satoshi_to_btc_str(recv_sat),
                        "outgoingActivityBtc": satoshi_to_btc_str(sent_sat),
                        "totalReceivedBtc": satoshi_to_btc_str(recv_sat),
                        "totalSentBtc": satoshi_to_btc_str(sent_sat),
                        "firstSeen": f_seen.isoformat() if f_seen else None,
                        "lastSeen": l_seen.isoformat() if l_seen else None,
                        "activeDays": act_days,
                        "riskExposure": "low",
                        "clusterId": None,
                    },
                }

            for aid in visited_addrs:
                if aid not in addr_dict:
                    addr_dict[aid] = {
                        "id": aid,
                        "label": f"{aid[:8]}...{aid[-4:]}" if len(aid) > 12 else aid,
                        "nodeType": "address",
                        "riskScore": None,
                        "riskLevel": None,
                        "behaviorType": None,
                        "metadata": {
                            "address": aid,
                            "addressType": "standard",
                            "transactionCount": 1,
                            "incomingActivityBtc": "0.00000000",
                            "outgoingActivityBtc": "0.00000000",
                            "totalReceivedBtc": "0.00000000",
                            "totalSentBtc": "0.00000000",
                            "firstSeen": None,
                            "lastSeen": None,
                            "activeDays": None,
                            "riskExposure": "low",
                            "clusterId": None,
                        },
                    }

            if analysis_id:
                ml_addr_query = (
                    f"SELECT entity_id, anomaly_score, risk_score, risk_level, prediction_label, "
                    f"       confidence, explanation_json, features_json, graph_evidence_json, model_id "
                    f"FROM ml_results WHERE dataset_id = ? AND analysis_id = ? "
                    f"  AND entity_type = 'address' AND entity_id IN ({ph})"
                )
                ml_addr_params = [dataset_id, analysis_id] + addr_list
            else:
                ml_addr_query = (
                    f"SELECT entity_id, anomaly_score, risk_score, risk_level, prediction_label, "
                    f"       confidence, explanation_json, features_json, graph_evidence_json, model_id "
                    f"FROM ml_results WHERE dataset_id = ? "
                    f"  AND entity_type = 'address' AND entity_id IN ({ph})"
                )
                ml_addr_params = [dataset_id] + addr_list

            ml_addr_rows = self.conn.execute(ml_addr_query, ml_addr_params).fetchall()
            for r in ml_addr_rows:
                aid, anom, r_score, r_lvl, pred_lbl, conf, exp_json, feat_json, gr_ev_json, m_id = r
                if aid in addr_dict:
                    explanation = _safe_json_loads(exp_json)
                    features = _safe_json_loads(feat_json)
                    graph_ev = _safe_json_loads(gr_ev_json)

                    addr_dict[aid]["riskScore"] = r_score
                    addr_dict[aid]["riskLevel"] = r_lvl.lower() if r_lvl else None
                    addr_dict[aid]["behaviorType"] = pred_lbl
                    m = addr_dict[aid]["metadata"]
                    m["riskScore"] = r_score
                    m["riskLevel"] = r_lvl.lower() if r_lvl else None
                    m["riskExposure"] = r_lvl.lower() if r_lvl else "low"
                    m["behavior"] = pred_lbl

                    if "evidence" not in m:
                        m["evidence"] = {"graph": {}, "temporal": {}, "network": {}, "ml": {}}

                    m["evidence"]["ml"]["riskScore"] = r_score
                    m["evidence"]["ml"]["riskLevel"] = r_lvl.lower() if r_lvl else None
                    m["evidence"]["ml"]["behaviorClassification"] = pred_lbl
                    m["evidence"]["ml"]["confidence"] = conf
                    m["evidence"]["ml"]["modelId"] = m_id
                    if isinstance(explanation, dict) and "top_features" in explanation:
                        m["evidence"]["ml"]["topFeatures"] = explanation["top_features"]
                    elif isinstance(explanation, list) and len(explanation) > 0:
                        m["evidence"]["ml"]["topFeatures"] = explanation

        # 5. Query Directed Bipartite Edges
        edges_list: List[Dict[str, Any]] = []
        if visited_txs and visited_addrs:
            tx_list = list(visited_txs)
            addr_list = list(visited_addrs)
            tx_ph = ", ".join("?" for _ in tx_list)
            addr_ph = ", ".join("?" for _ in addr_list)

            # Input edges: address -> transaction
            in_edge_query = f"""
            SELECT i.input_address, i.transaction_id, i.input_value_satoshi, t.timestamp
            FROM transaction_inputs i
            JOIN transactions t ON i.transaction_id = t.transaction_id AND i.dataset_id = t.dataset_id
            WHERE i.dataset_id = ?
              AND i.transaction_id IN ({tx_ph})
              AND i.input_address IN ({addr_ph})
            """
            in_edge_rows = self.conn.execute(in_edge_query, [dataset_id] + tx_list + addr_list).fetchall()
            for src_addr, tgt_tx, val_sat, ts in in_edge_rows:
                val_sat = val_sat or 0
                val_btc = satoshi_to_btc_str(val_sat)
                edges_list.append({
                    "id": f"{src_addr}→{tgt_tx}",
                    "source": src_addr,
                    "target": tgt_tx,
                    "edgeType": "input",
                    "totalValueBtc": val_btc,
                    "totalValueSatoshi": val_sat,
                    "valueBtc": val_btc,
                    "valueSatoshi": val_sat,
                    "transactionCount": 1,
                    "timestamp": ts.isoformat() if ts else None,
                    "transactions": [{
                        "transactionId": tgt_tx,
                        "valueSatoshi": val_sat,
                        "valueBtc": val_btc,
                        "timestamp": ts.isoformat() if ts else None,
                    }],
                })

            # Output edges: transaction -> address
            out_edge_query = f"""
            SELECT o.transaction_id, o.output_address, o.output_value_satoshi, t.timestamp
            FROM transaction_outputs o
            JOIN transactions t ON o.transaction_id = t.transaction_id AND o.dataset_id = t.dataset_id
            WHERE o.dataset_id = ?
              AND o.transaction_id IN ({tx_ph})
              AND o.output_address IN ({addr_ph})
            """
            out_edge_rows = self.conn.execute(out_edge_query, [dataset_id] + tx_list + addr_list).fetchall()
            for src_tx, tgt_addr, val_sat, ts in out_edge_rows:
                val_sat = val_sat or 0
                val_btc = satoshi_to_btc_str(val_sat)
                edges_list.append({
                    "id": f"{src_tx}→{tgt_addr}",
                    "source": src_tx,
                    "target": tgt_addr,
                    "edgeType": "output",
                    "totalValueBtc": val_btc,
                    "totalValueSatoshi": val_sat,
                    "valueBtc": val_btc,
                    "valueSatoshi": val_sat,
                    "transactionCount": 1,
                    "timestamp": ts.isoformat() if ts else None,
                    "transactions": [{
                        "transactionId": src_tx,
                        "valueSatoshi": val_sat,
                        "valueBtc": val_btc,
                        "timestamp": ts.isoformat() if ts else None,
                    }],
                })

        # Populate address structural graph metrics
        for aid, node in addr_dict.items():
            in_edges = [e for e in edges_list if e["target"] == aid]
            out_edges = [e for e in edges_list if e["source"] == aid]
            m = node["metadata"]
            if "evidence" not in m:
                m["evidence"] = {"graph": {}, "temporal": {}, "network": {}, "ml": {}}
            m["evidence"]["graph"]["neighborCount"] = len(in_edges) + len(out_edges)
            m["evidence"]["graph"]["fanIn"] = len(in_edges)
            m["evidence"]["graph"]["fanOut"] = len(out_edges)
            m["evidence"]["graph"]["addressReuse"] = (m.get("transactionCount") or 0) > 1
            m["evidence"]["graph"]["clusterId"] = m.get("clusterId")

        # 6. High Risk Filtering (risk_score >= 0.50)
        all_nodes_map = {**tx_dict, **addr_dict}

        if high_risk_only:
            kept_node_ids = {entity_id}
            high_risk_tx_ids = {
                tid for tid, node in tx_dict.items()
                if (node.get("riskScore") is not None and node["riskScore"] >= 0.50)
                or (node.get("riskLevel") in ("high", "critical"))
            }
            kept_node_ids.update(high_risk_tx_ids)

            for e in edges_list:
                if e["source"] in high_risk_tx_ids:
                    kept_node_ids.add(e["target"])
                if e["target"] in high_risk_tx_ids:
                    kept_node_ids.add(e["source"])

            final_nodes = [node for nid, node in all_nodes_map.items() if nid in kept_node_ids]
            final_edges = [
                e for e in edges_list
                if e["source"] in kept_node_ids and e["target"] in kept_node_ids
            ]
        else:
            final_nodes = list(all_nodes_map.values())
            final_edges = edges_list

        # 7. Selected Entity Information & Alerts
        alerts_by_entity: Dict[str, List[Dict[str, Any]]] = {}
        try:
            has_alerts = self.conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'alerts'"
            ).fetchone()[0] > 0
            if has_alerts and final_nodes:
                all_ids = [n["id"] for n in final_nodes]
                ph_alerts = ", ".join("?" for _ in all_ids)
                alert_sql = f"SELECT entity_id, alert_id, alert_type, severity, priority, status FROM alerts WHERE entity_id IN ({ph_alerts})"
                alert_params = all_ids
                if analysis_id:
                    alert_sql += " AND (analysis_id = ? OR analysis_id IS NULL)"
                    alert_params.append(analysis_id)
                alert_sql += " ORDER BY created_at DESC"
                for a_row in self.conn.execute(alert_sql, alert_params).fetchall():
                    eid = a_row[0]
                    if eid not in alerts_by_entity:
                        alerts_by_entity[eid] = []
                    alerts_by_entity[eid].append({
                        "alertId": a_row[1],
                        "alertType": a_row[2],
                        "severity": a_row[3],
                        "priority": a_row[4],
                        "status": a_row[5],
                    })
        except Exception as e:
            logger.debug(f"Alert lookup exception: {e}")

        for n in final_nodes:
            n_alerts = alerts_by_entity.get(n["id"], [])
            n["alerts"] = n_alerts
            if n.get("metadata") is not None:
                n["metadata"]["alerts"] = n_alerts

        selected_node = all_nodes_map.get(entity_id)
        selected_label = selected_node["label"] if selected_node else (entity_id[:8] + "..." if len(entity_id) > 12 else entity_id)
        selected_risk_score = selected_node.get("riskScore") if selected_node else None
        selected_risk_level = selected_node.get("riskLevel") if selected_node else None
        selected_behavior = selected_node.get("behaviorType") if selected_node else None
        selected_metadata = selected_node.get("metadata") if selected_node else {}

        selected_entity_dict = {
            "entityId": entity_id,
            "entityType": resolved_type,
            "label": selected_label,
            "exists": True,
            "riskScore": selected_risk_score,
            "riskLevel": selected_risk_level,
            "behaviorType": selected_behavior,
            "metadata": selected_metadata,
            "alerts": alerts_by_entity.get(entity_id, []),
        }

        summary = {
            "nodeCount": len(final_nodes),
            "edgeCount": len(final_edges),
            "depth": depth,
            "highRiskOnly": high_risk_only,
            "addressCount": sum(1 for n in final_nodes if n["nodeType"] == "address"),
            "transactionCount": sum(1 for n in final_nodes if n["nodeType"] == "transaction"),
            "clusterCount": 0,
        }

        return {
            "graphId": str(uuid.uuid4()),
            "analysisId": analysis_id,
            "datasetId": dataset_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "selectedEntity": selected_entity_dict,
            "summary": summary,
            "nodes": final_nodes,
            "edges": final_edges,
            "isSubgraph": True,
            "subgraphCenter": entity_id,
            "nodeCount": len(final_nodes),
            "edgeCount": len(final_edges),
        }
