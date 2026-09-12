# Visualization Specification

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Cytoscape.js Graph Visualization

### 1.1 Graph Element Mapping

The backend graph export (see [graph-schema.md](../graph/graph-schema.md)) is transformed to Cytoscape.js elements:

```typescript
function graphExportToCytoscape(graphData: GraphExport): ElementDefinition[] {
  return [
    ...graphData.nodes.map(node => ({
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.nodeType,
        riskScore: node.riskScore ?? null,
        riskLevel: node.riskLevel ?? null,
        transactionCount: node.metadata?.transactionCount ?? null,
        totalReceivedBtc: node.metadata?.totalReceivedBtc ?? null,
      }
    })),
    ...graphData.edges.map(edge => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        totalValueBtc: edge.totalValueBtc,
        transactionCount: edge.transactionCount,
        edgeType: edge.edgeType,
      }
    }))
  ];
}
```

### 1.2 Node Color Scheme

Nodes are colored by risk level:

| Risk Level | Color | Tailwind | Hex |
|---|---|---|---|
| `critical` | Red | `bg-red-600` | `#DC2626` |
| `high` | Orange | `bg-orange-500` | `#F97316` |
| `medium` | Yellow | `bg-yellow-400` | `#FACC15` |
| `low` | Green | `bg-green-500` | `#22C55E` |
| `null` (unanalyzed) | Gray | `bg-gray-400` | `#9CA3AF` |

### 1.3 Node Size

Node size scales with `transactionCount` (log-normalized):

```javascript
// Cytoscape style
style: {
  'width': function(node) {
    const count = node.data('transactionCount') || 1;
    return Math.max(20, Math.min(80, Math.log10(count) * 20));
  },
  'height': 'data(width)',
}
```

### 1.4 Edge Width

Edge width scales with `totalValueBtc` (log-normalized):

```javascript
style: {
  'width': function(edge) {
    const val = parseFloat(edge.data('totalValueBtc') || '0');
    return Math.max(1, Math.min(10, Math.log10(val + 1) * 2));
  }
}
```

### 1.5 Layout Algorithm

Proposed: `cose-bilkent` layout (physics-based, good for Bitcoin transaction graphs).

Alternative: `dagre` (hierarchical — useful for transaction flow view).

`DECISION REQUIRED`: Final layout choice.

---

## 2. Recharts Visualizations

### 2.1 Risk Distribution Chart

**Purpose**: Show the distribution of risk scores across all analyzed entities.

**Chart type**: Histogram (Bar chart with 10 bins: 0–0.1, 0.1–0.2, ..., 0.9–1.0)

**Recharts component**: `<BarChart>` from recharts

**Data**: Computed from `GET /api/analyses/{analysisId}/results` (aggregated client-side or via a summary endpoint)

**Color scheme**: Gradient from green (low scores) to red (high scores) per bin.

---

### 2.2 Transaction Value Over Time

**Purpose**: Show Bitcoin transaction volume over time for a dataset.

**Chart type**: Line chart or Area chart

**Recharts component**: `<AreaChart>`

**X-axis**: Timestamp (grouped by day or week)

**Y-axis**: Total transaction value in BTC

---

### 2.3 Top Risk Entities Bar Chart

**Purpose**: Bar chart of top 10 highest-risk addresses.

**Chart type**: Horizontal bar chart

**Recharts component**: `<BarChart layout="vertical">`

**X-axis**: Risk score (0–1)

**Color**: Colored by risk level.

---

### 2.4 SHAP Explanation Waterfall

**Purpose**: For a specific entity, show SHAP feature contributions.

**Chart type**: Custom horizontal bar chart (sorted by |SHAP value|)

**Direction**: Bars to the right = increases risk (red); bars to the left = decreases risk (green)

**Label**: Feature display label on Y-axis

This replaces a pure waterfall chart (complex to implement) with a horizontal sorted bar chart.

---

## 3. Risk Badge Component

Used everywhere a risk level needs to be shown inline:

```tsx
const riskColors = {
  critical: 'bg-red-600 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-400 text-gray-900',
  low: 'bg-green-500 text-white',
};

function RiskBadge({ level }: { level: string | null }) {
  if (!level) return <span className="text-gray-400">—</span>;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${riskColors[level]}`}>
      {level}
    </span>
  );
}
```

---

## 4. Explanation Card Component

Used to display a single SHAP feature explanation:

```
┌─────────────────────────────────────────────────┐
│ ▲ Transaction velocity per day      importance 1 │
│                                                  │
│ Value: 47.3 tx/day                               │
│ ████████████████████░░░░░  contributes HIGH risk │
└─────────────────────────────────────────────────┘
```

- ▲ = increases risk (red), ▼ = decreases risk (green)
- Bar width = `normalizedImportance * 100%`
- Color = red if `direction === 'increases_risk'`, green otherwise

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Frontend Owner*
*References: [graph-schema.md](../graph/graph-schema.md) | [model-output-contract.md](../ml/model-output-contract.md)*
