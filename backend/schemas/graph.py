"""Graph export schemas matching docs/graph/graph-schema.md."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.schemas.common import CamelModel


class NodeMetadata(CamelModel):
    transaction_count: Optional[int] = None
    total_received_btc: Optional[str] = None
    total_sent_btc: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    active_days: Optional[int] = None


class GraphNode(CamelModel):
    id: str
    label: str
    node_type: str = "address"
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    behavior_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    alerts: Optional[List[Dict[str, Any]]] = None


class GraphEdgeTransaction(CamelModel):
    transaction_id: str
    value_satoshi: int
    value_btc: str
    timestamp: Optional[str] = None


class GraphEdge(CamelModel):
    id: str
    source: str
    target: str
    edge_type: str = "transaction"
    transactions: List[GraphEdgeTransaction] = []
    total_value_btc: Optional[str] = "0.00000000"
    total_value_satoshi: Optional[int] = 0
    transaction_count: Optional[int] = 0
    value_btc: Optional[str] = None
    value_satoshi: Optional[int] = None
    timestamp: Optional[str] = None


class GraphExport(CamelModel):
    graph_id: str
    analysis_id: Optional[str] = None
    dataset_id: str
    generated_at: str
    node_count: int
    edge_count: int
    is_subgraph: bool = False
    subgraph_center: Optional[str] = None
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


class SelectedEntityInfo(CamelModel):
    entity_id: str
    entity_type: str
    label: Optional[str] = None
    exists: bool = True
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    behavior_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    alerts: Optional[List[Dict[str, Any]]] = None


class GraphSummary(CamelModel):
    node_count: int
    edge_count: int
    depth: int
    high_risk_only: bool
    address_count: int = 0
    transaction_count: int = 0
    cluster_count: int = 0


class GraphNeighborhoodResponse(CamelModel):
    graph_id: str
    analysis_id: Optional[str] = None
    dataset_id: str
    generated_at: str
    selected_entity: SelectedEntityInfo
    summary: GraphSummary
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    is_subgraph: bool = True
    subgraph_center: Optional[str] = None
    node_count: Optional[int] = None
    edge_count: Optional[int] = None
