# Graph Schema

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative graph node/edge schema.**
> The Backend API must serialize graph data in this format.
> The Frontend (Cytoscape.js) consumes this format.
> Do NOT change field names without updating this document and coordinating with the Backend and Frontend owners.

---

## 1. Graph Export Format

The graph is serialized as a JSON object with `nodes` and `edges` arrays.

```json
{
  "graphId": "string (UUID)",
  "analysisId": "string (UUID)",
  "datasetId": "string (UUID)",
  "generatedAt": "ISO 8601 UTC datetime",
  "nodeCount": 1234,
  "edgeCount": 5678,
  "isSubgraph": false,
  "subgraphCenter": null,
  "nodes": [ ...NodeObject... ],
  "edges": [ ...EdgeObject... ]
}
```

---

## 2. Node Schema

Each node represents a Bitcoin address.

```json
{
  "id": "string",
  "label": "string",
  "nodeType": "address",
  "riskScore": 0.82,
  "riskLevel": "high",
  "metadata": {
    "transactionCount": 142,
    "totalReceivedBtc": "5.00000000",
    "totalSentBtc": "4.99000000",
    "firstSeen": "2009-01-12T03:30:25+00:00",
    "lastSeen": "2009-03-14T12:00:00+00:00",
    "activeDays": 61
  }
}
```

### Node Field Definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Yes | Bitcoin address string. This IS the node identifier. |
| `label` | `string` | Yes | Short display label. For addresses: first 8 + "..." + last 4 chars. |
| `nodeType` | `string (enum)` | Yes | Currently always `"address"` |
| `riskScore` | `float \| null` | No | Risk score from ML result [0.0, 1.0]. Null if not yet analyzed. |
| `riskLevel` | `string (enum) \| null` | No | `"low"` / `"medium"` / `"high"` / `"critical"` / null |
| `metadata.transactionCount` | `integer` | No | Number of transactions |
| `metadata.totalReceivedBtc` | `string` | No | BTC received as 8-decimal string |
| `metadata.totalSentBtc` | `string` | No | BTC sent as 8-decimal string |
| `metadata.firstSeen` | `string (ISO 8601)` | No | First transaction timestamp |
| `metadata.lastSeen` | `string (ISO 8601)` | No | Last transaction timestamp |
| `metadata.activeDays` | `integer` | No | Days between first and last seen |

**Important**: BTC values are returned as **string-encoded 8-decimal-place numbers** (not JSON floats) to avoid precision loss. Example: `"5.00000000"` not `5.0`.

---

## 3. Edge Schema

Each edge represents a value flow from one address to another via a transaction.

```json
{
  "id": "string",
  "source": "string",
  "target": "string",
  "edgeType": "transaction",
  "transactions": [
    {
      "transactionId": "string",
      "valueSatoshi": 500000000,
      "valueBtc": "5.00000000",
      "timestamp": "2009-01-12T03:30:25+00:00"
    }
  ],
  "totalValueBtc": "5.00000000",
  "totalValueSatoshi": 500000000,
  "transactionCount": 1
}
```

### Edge Field Definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Yes | Edge identifier. Format: `"{source_address}→{target_address}"` or `"{txid}:{output_index}"` |
| `source` | `string` | Yes | Source address node `id` |
| `target` | `string` | Yes | Target address node `id` |
| `edgeType` | `string (enum)` | Yes | `"transaction"` or `"aggregated"` |
| `transactions` | `array` | Yes | List of transactions composing this edge |
| `transactions[].transactionId` | `string` | Yes | Bitcoin transaction ID |
| `transactions[].valueSatoshi` | `integer` | Yes | Value in satoshis |
| `transactions[].valueBtc` | `string` | Yes | Value as 8-decimal BTC string |
| `transactions[].timestamp` | `string \| null` | No | Transaction timestamp (ISO 8601 UTC) |
| `totalValueBtc` | `string` | Yes | Sum of all transaction values (BTC string) |
| `totalValueSatoshi` | `integer` | Yes | Sum of all transaction values (satoshis) |
| `transactionCount` | `integer` | Yes | Number of transactions composing this edge |

---

## 4. Graph Metadata Fields

| Field | Type | Description |
|---|---|---|
| `graphId` | `string (UUID)` | Unique identifier for this graph export |
| `analysisId` | `string (UUID)` | Which analysis run this graph belongs to |
| `datasetId` | `string (UUID)` | Source dataset |
| `generatedAt` | `string (ISO 8601 UTC)` | When graph was generated |
| `nodeCount` | `integer` | Total nodes in this export |
| `edgeCount` | `integer` | Total edges in this export |
| `isSubgraph` | `boolean` | True if this is a neighborhood subgraph, not the full graph |
| `subgraphCenter` | `string \| null` | Center node ID if this is a neighborhood subgraph |

---

## 5. Cytoscape.js Mapping

The frontend transforms the graph export into Cytoscape.js data format:

```javascript
// From backend graph export to Cytoscape elements
const cytoscapeElements = [
  // Nodes
  ...graphData.nodes.map(node => ({
    data: {
      id: node.id,
      label: node.label,
      nodeType: node.nodeType,
      riskScore: node.riskScore,
      riskLevel: node.riskLevel,
      // Flatten metadata for Cytoscape
      transactionCount: node.metadata?.transactionCount,
      totalReceivedBtc: node.metadata?.totalReceivedBtc,
    }
  })),
  // Edges
  ...graphData.edges.map(edge => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      edgeType: edge.edgeType,
      totalValueBtc: edge.totalValueBtc,
      transactionCount: edge.transactionCount,
    }
  }))
];
```

See [visualization-specification.md](../frontend/visualization-specification.md) for the full Cytoscape.js configuration.

---

## 6. What the Frontend Must NOT Do

- Must not reconstruct graph semantics from raw API data outside this schema
- Must not redefine what `source` and `target` mean
- Must not assume `riskScore` is always present (it is null if analysis hasn't run)
- Must not perform graph analysis in the browser
- Must not call DuckDB or ML directly

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: ML Owner + Backend Owner + Frontend Owner (joint)*
*References: [graph-construction.md](./graph-construction.md) | [visualization-specification.md](../frontend/visualization-specification.md) | [api-specification.md](../backend/api-specification.md)*
