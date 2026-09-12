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
    metadata: Optional[NodeMetadata] = None


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
    total_value_btc: str
    total_value_satoshi: int
    transaction_count: int


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
