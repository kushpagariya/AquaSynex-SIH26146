# End-to-End Scenarios

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> These scenarios define the expected end-to-end system behavior from the investigator's perspective.
> They double as integration test scenarios.

---

## Scenario 1: Upload and Process Dataset

**Actor**: Investigator
**Precondition**: System running (Docker Compose up); no datasets loaded.

**Steps**:
1. Navigate to `http://localhost:3000`
2. Go to Datasets page
3. Enter dataset name: "Elliptic Demo"
4. Select CSV file containing 50,000 transactions
5. Click Upload

**Expected**:
- Upload progress shown
- Dataset status shows "Processing"
- After ~30 seconds, status changes to "Ready"
- Row count displayed: 50,000
- Available fields list shown

**Backend verification**:
```bash
curl http://localhost:8000/api/datasets
# Returns dataset with status="ready", rowCount=50000
```

---

## Scenario 2: Run Analysis on Dataset

**Actor**: Investigator
**Precondition**: Dataset in "ready" status.

**Steps**:
1. Select dataset from list
2. Click "Analyze"
3. Select default model (isolation_forest_v1)
4. Click "Start Analysis"

**Expected**:
- Analysis status: "Pending" → "Running" → "Completed"
- After completion: shows entity count, high-risk count, critical count
- Navigation links appear: "View Transactions", "View Addresses", "View Graph"

---

## Scenario 3: Explore High-Risk Addresses

**Actor**: Investigator
**Precondition**: Analysis completed.

**Steps**:
1. Navigate to Addresses
2. Filter by "High" and "Critical" risk level
3. Sort by risk score descending
4. Click top result

**Expected**:
- Address detail page loads
- Shows: address string, risk score, risk badge, transaction count, BTC totals
- SHAP explanation cards shown (top 5 features)
- Each card shows feature name, direction indicator, feature value, importance bar
- Neighborhood graph shown (Cytoscape.js, 2 hops)
- Graph nodes colored by risk level

---

## Scenario 4: Graph Exploration

**Actor**: Investigator
**Precondition**: Analysis completed.

**Steps**:
1. Navigate to Graph view
2. Filter: show only high + critical risk nodes
3. Click on a high-risk node

**Expected**:
- Graph renders with risk-colored nodes
- Click opens address detail panel (sidebar)
- Panel shows risk score, explanation cards

---

## Scenario 5: Transaction Exploration

**Actor**: Investigator
**Precondition**: Analysis completed.

**Steps**:
1. Navigate to Transactions
2. Filter: min risk score 0.7, date range applied
3. Click on transaction

**Expected**:
- Transaction detail: inputs, outputs with addresses and BTC values
- Risk score displayed
- Link to address detail for each input/output address

---

## Scenario 6: Offline Operation

**Precondition**: System running, all images and data loaded.

**Steps**:
1. Disconnect machine from internet
2. Reload `http://localhost:3000`

**Expected**:
- Frontend loads normally
- All API calls succeed
- Analysis completes normally
- Graph renders normally
- No CDN errors in browser console

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
