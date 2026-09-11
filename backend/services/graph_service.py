"""Graph analytics integration service and graph exporter.

Authoritative reference: docs/graph/graph-schema.md
Builds Cytoscape-compatible graph JSON from canonical transaction records and ML risk scores.
"""

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import duckdb
from backend.db.queries import analyses as analysis_queries
from backend.utils.converters import satoshi_to_btc_str
from backend.utils.errors import AnalysisNotFoundError, GraphNotAvailableError
from backend.utils.logging import logger


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
