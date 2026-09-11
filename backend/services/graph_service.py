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
        edge_query = """
        SELECT 
            i.input_address AS source,
            o.output_address AS target,
            t.transaction_id,
            o.output_value_satoshi AS value_satoshi,
            t.timestamp
        FROM transaction_inputs i
        JOIN transaction_outputs o ON i.transaction_id = o.transaction_id AND i.dataset_id = o.dataset_id
        JOIN transactions t ON i.transaction_id = t.transaction_id AND i.dataset_id = t.dataset_id
        WHERE i.dataset_id = ?
          AND i.input_address IS NOT NULL
          AND o.output_address IS NOT NULL
          AND i.input_address != o.output_address
        """
        edge_params = [dataset_id]

        if not include_neighbors and selected_address_ids:
            # Only edges where both source and target are in selected_address_ids
            addr_list_str = ", ".join(f"'{a}'" for a in selected_address_ids)
            edge_query += f" AND i.input_address IN ({addr_list_str}) AND o.output_address IN ({addr_list_str})"

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

        # Find which dataset contains this address
        addr_row = self.conn.execute(
            "SELECT dataset_id FROM addresses WHERE address_id = ? LIMIT 1", [address_id]
        ).fetchone()

        dataset_id = addr_row[0] if addr_row else None
        if not dataset_id:
            # Check transaction inputs/outputs if not in addresses table
            in_row = self.conn.execute(
                "SELECT dataset_id FROM transaction_inputs WHERE input_address = ? LIMIT 1", [address_id]
            ).fetchone()
            dataset_id = in_row[0] if in_row else None

        if not dataset_id:
            raise GraphNotAvailableError(f"Address '{address_id}' not found in any dataset.")

        # Breadth-first search for N-hop neighbors
        visited_nodes: Set[str] = {address_id}
        queue: deque = deque([(address_id, 0)])

        while queue:
            curr_addr, curr_hop = queue.popleft()
            if curr_hop >= hops:
                continue

            # Find neighbors: outputs received from transactions where curr_addr was input
            fwd_rel = self.conn.execute(
                """
                SELECT DISTINCT o.output_address
                FROM transaction_inputs i
                JOIN transaction_outputs o ON i.transaction_id = o.transaction_id AND i.dataset_id = o.dataset_id
                WHERE i.dataset_id = ? AND i.input_address = ? AND o.output_address IS NOT NULL AND o.output_address != ?
                LIMIT 50
                """,
                [dataset_id, curr_addr, curr_addr],
            )
            for (nbr,) in fwd_rel.fetchall():
                if nbr not in visited_nodes:
                    visited_nodes.add(nbr)
                    queue.append((nbr, curr_hop + 1))

            # Find neighbors: inputs spent to transactions where curr_addr was output
            bwd_rel = self.conn.execute(
                """
                SELECT DISTINCT i.input_address
                FROM transaction_outputs o
                JOIN transaction_inputs i ON o.transaction_id = i.transaction_id AND o.dataset_id = i.dataset_id
                WHERE o.dataset_id = ? AND o.output_address = ? AND i.input_address IS NOT NULL AND i.input_address != ?
                LIMIT 50
                """,
                [dataset_id, curr_addr, curr_addr],
            )
            for (nbr,) in bwd_rel.fetchall():
                if nbr not in visited_nodes:
                    visited_nodes.add(nbr)
                    queue.append((nbr, curr_hop + 1))

        # Retrieve nodes detail
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        for addr in visited_nodes:
            row = self.conn.execute(
                """
                SELECT a.transaction_count, a.total_received_satoshi, a.total_sent_satoshi,
                       a.first_seen_timestamp, a.last_seen_timestamp,
                       r.risk_score, r.risk_level
                FROM addresses a
                LEFT JOIN ml_results r ON a.address_id = r.entity_id AND a.dataset_id = r.dataset_id
                WHERE a.address_id = ? AND a.dataset_id = ?
                LIMIT 1
                """,
                [addr, dataset_id],
            ).fetchone()

            tx_cnt, recv_sat, sent_sat, first_seen, last_seen, r_score, r_lvl = row if row else (0, 0, 0, None, None, None, None)
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
        addr_list_str = ", ".join(f"'{a}'" for a in visited_nodes)
        edge_query = f"""
        SELECT 
            i.input_address AS source,
            o.output_address AS target,
            t.transaction_id,
            o.output_value_satoshi AS value_satoshi,
            t.timestamp
        FROM transaction_inputs i
        JOIN transaction_outputs o ON i.transaction_id = o.transaction_id AND i.dataset_id = o.dataset_id
        JOIN transactions t ON i.transaction_id = t.transaction_id AND i.dataset_id = t.dataset_id
        WHERE i.dataset_id = ?
          AND i.input_address IN ({addr_list_str})
          AND o.output_address IN ({addr_list_str})
          AND i.input_address != o.output_address
        """
        edge_rel = self.conn.execute(edge_query, [dataset_id])

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
