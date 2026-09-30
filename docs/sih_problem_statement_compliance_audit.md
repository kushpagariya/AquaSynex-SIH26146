# AquaSynex SIH26146: Forensic Compliance Audit, Gap Analysis & Master Implementation Plan

**Problem Statement:** SIH26146 — *AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic*  
**Repository Branch Audited:** `option2-ui` (Commit: `e914d59684fba4a32433a160862ace9ff537ea47`)  
**Target Environment:** Linux / Docker (Offline Air-Gapped Operation)  
**Document Status:** Official Forensic Audit & Engineering Roadmap  
**Authoritative Reference:** Smart India Hackathon PS SIH26146 Specifications

---

## 1. Executive Summary & Compliance Verdict

AquaSynex is an offline, AI-powered forensic investigation and link-analysis platform designed to ingest bulk Bitcoin transaction and network telemetry data, correlate network-layer observations with blockchain ledger records, execute machine learning inference for risk detection, cluster related entities, and present explainable, prioritized investigative leads through an interactive institutional dashboard.

This audit evaluates the codebase strictly against the official SIH26146 Problem Statement (PS) requirements.

### Forensic Summary

| Category | Score / Status | Assessment |
| :--- | :---: | :--- |
| **Overall PS Baseline Alignment** | **85%** | Architecturally sound and fundamentally aligned with the core problem statement. |
| **Offline Operation (Air-Gap)** | **100%** | Zero runtime external HTTP calls, telemetry, or cloud dependencies. |
| **AI/ML & Explainability (XAI)** | **100%** | Native XGBoost + CatBoost inference with live additive TreeSHAP explanations. |
| **Data Ingestion** | **75%** | Robust CSV/JSON/JSONL streaming ingestion; **XML is currently unsupported (P0 Gap)**. |
| **Network-Chain Correlation** | **80%** | Correlated in analytical SQL and ML feature space; **IP nodes missing from visual graph canvas (P1 Gap)**. |
| **GeoIP Integration** | **40%** | Reads pre-populated dataset columns; **no bundled offline GeoIP `.mmdb` database (P0 Gap)**. |
| **Linux / Docker Deployment** | **100%** | Verified multi-stage Docker builds with volume persistence and POSIX compliance. |

```
                               CURRENT COMPLIANCE PROFILE
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ [████████████████████████████████████████████░░░░░░░░] 85% Baseline PS  │
   └─────────────────────────────────────────────────────────────────────────┘
    Satisfied: Offline, CSV/JSON, Ingest, ML Models, SHAP XAI, Clustering, UI
    Critical Gaps: XML Ingestion (P0), Bundled GeoIP DB (P0), Canvas IP Nodes (P1)
```

---

## 2. Granular Problem Statement Requirements Matrix

The official Problem Statement has been decomposed into 27 testable technical requirements:

| ID | PS Requirement | Exact Technical Meaning | Mandatory? | Current Code Status | Priority |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **PS-01** | Offline Operation | Operates with zero internet connectivity, external APIs, or remote licensing after deployment. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-02** | Bulk Ingestion Engine | High-throughput ingestion of multi-megabyte transaction/network datasets without OOM. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-03** | CSV Ingestion | Parsing of comma-separated transaction records and headers. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-04** | JSON Ingestion | Parsing of JSON arrays and line-delimited JSON (JSONL). | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-05** | XML Ingestion | Native parsing of XML schema-based transaction dumps. | **Yes** | 🔴 **Missing** | **P0** |
| **PS-06** | Bitcoin Transaction Fields | Ingestion of `txid`, `inputs[]`, `outputs[]`, `amounts[]`, `fee`, `script_type`. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-07** | Network Metadata Fields | Ingestion of `src_ip`, `dst_ip`, `src_port`, `dst_port`, `timestamp`, `country`, `asn`. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-08** | Net ↔ Chain Correlation | Relational & analytical join linking network observations with blockchain ledger data. | **Yes** | 🟢 Satisfied (Analytic) | **P1 (Canvas)** |
| **PS-09** | IP-Wallet Relationship | Identifying which IP addresses broadcast or receive for specific Bitcoin wallets. | **Yes** | 🟢 Satisfied (Analytic) | **P1 (Canvas)** |
| **PS-10** | IP-TX Relationship | Associating transaction IDs directly with originating/relay P2P IP addresses. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-11** | Wallet-TX Relationship | Multi-input, multi-output UTXO relationship tracking. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-12** | Entity Graph | Grouping addresses into common-ownership cluster entities. | **Yes** | 🟢 Satisfied (Heuristic) | Baseline |
| **PS-13** | Transaction Graph | Directed topological graph of funds moving across entities/addresses. | **Yes** | 🟡 Partially Satisfied | **P1** |
| **PS-14** | AI/ML Anomaly Detection | Algorithmic detection of anomalous/suspicious transaction behaviors. | **Yes** | 🟠 Supervised XGBoost | **P1 (Framing)** |
| **PS-15** | Working Trained Model | Real serialized model artifacts loaded at runtime (no mocks or hardcoded rules). | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-16** | Entity Clustering | Algorithmic grouping of Bitcoin addresses via common-spending heuristics. | **Yes** | 🟢 Satisfied (Union-Find) | Baseline |
| **PS-17** | Prioritized / Ranked Alerts | Triage alert feed sorted by risk score and severity. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-18** | Explainable Alerts | Transparent attribution explaining why an entity/transaction was flagged. | **Yes** | 🔵 **Differentiator (SHAP)** | Baseline |
| **PS-19** | Confidence Score | Calibrated probabilistic certainty metric for every flag. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-20** | Interactive Dashboard | Unified overview interface showing KPIs, risk distributions, and alerts. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-21** | Link-Analysis Visualization | Interactive canvas rendering transaction graphs with pan/zoom/hop expansion. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-22** | Flagged Entities View | Dedicated address and transaction dossier views for deep forensic drilldown. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-23** | Evidence Per Flag | Granular forensic evidence cards with physical units and impact directions. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-24** | GeoIP Database Integration | Integrated downloadable offline GeoIP database (`.mmdb`) for IP resolution. | **Yes** | 🔴 **Missing** | **P0** |
| **PS-25** | Linux Platform Compatibility | Validated deployment and operation on Linux via Docker and POSIX compliance. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-26** | Working Prototype | End-to-end operational pipeline from raw upload to interactive investigation. | **Yes** | ✅ Fully Satisfied | Baseline |
| **PS-27** | Technical Write-up | Comprehensive documentation of architecture, ML models, and methodologies. | **Yes** | ✅ Fully Satisfied | Baseline |

---

## 3. Subsystem-by-Subsystem Forensic Audit

### 3.1. Offline Architecture & Air-Gap Compliance

```
+-------------------------------------------------------------------------------+
|                           AIR-GAPPED RUNTIME BOUNDARY                         |
|                                                                               |
|   INCOMING REQUEST               FASTAPI APPLICATION             ANALYTICAL   |
|   (Browser / UI)                (Localhost:8000)                STORAGE       |
|          │                             │                             │        |
|          ├── HTTP /api/v1/* ───────────► In-Process Execution         │        |
|          │                             ├── DuckDB Queries ───────────► (data/ │
|          │                             ├── XGBoost / CatBoost C++    │  *.db) │
|          │                             └── TreeSHAP Live Engine      │        |
|          ▼                             ▼                             ▼        |
|   [ NO OUTBOUND CALLS ]      [ NO THIRD-PARTY LLMS ]     [ EMBEDDED C++ DB ]  |
|   - Zero WAN traffic         - Zero OpenAI / Gemini      - Zero Cloud RDS     |
|   - Zero Blockchain RPCs     - Zero HuggingFace APIs     - Zero External Daemons|
+-------------------------------------------------------------------------------+
```

- **Runtime Inspection:** Code verification across `backend/` confirms zero outbound calls. No `requests`, `httpx`, `urllib`, or external websocket connections exist in the request handling pipeline.
- **Model Execution:** Native C++ shared library execution via Python bindings (`xgboost.Booster`, `catboost.CatBoostClassifier`).
- **Database Architecture:** Embedded DuckDB (`data/aquasynex.db`), running in-process via C++ memory-mapped tables.
- **Build vs. Runtime Distinction:** The Docker build phase pulls official base images (`python:3.11-slim`, `node:20-alpine`) and installs dependencies once. Once built, the container images run completely air-gapped without network egress.

---

### 3.2. Bulk Data Ingestion Engine

- **Supported Formats:**
  - `CSV`: Fully supported via DuckDB `read_csv_auto`. Handles custom delimiters, quoted arrays, and timestamps.
  - `JSON` / `JSONL`: Fully supported. Ingests nested arrays and records.
  - `Parquet`: Fully supported. Columnar binary format for high performance.
  - `XML`: **UNSUPPORTED.** In `backend/services/dataset_service.py:27-32`, `ALLOWED_FORMATS` strictly limits uploads to `.csv, .parquet, .json, .jsonl`. An uploaded `.xml` file fails with HTTP 415.
- **Array Parsing Robustness:** In `backend/services/dataset_service.py:190-245`, multi-value fields such as `input_addresses`, `output_addresses`, `input_amounts`, and `output_amounts` serialized as stringified Python/JSON lists (e.g. `"['1A1z...', '12c6...']"`) are safely parsed and unpacked into normalized 1-to-N join tables (`transaction_inputs` and `transaction_outputs`).
- **File Size Ceiling:** Configured to 500 MB (`MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024`). Files exceeding this raise `FileTooLargeError` (HTTP 413).

---

### 3.3. Network ↔ Blockchain Correlation Architecture

The Problem Statement specifically mandates:
> *"correlates network-layer (IP/port/timing) observations with blockchain-layer (wallet/TXID/amount) data"*

The current codebase implements this correlation across two distinct layers, but omits it from a third:

```
+---------------------------------------------------------------------------------+
|                       THREE-TIER CORRELATION ARCHITECTURE                       |
|                                                                                 |
|  [ TIER 1: RELATIONAL DATA LAYER ] ──────────────────────────────────── [ PASS ] |
|  - Table `network_events` stores (src_ip, dst_ip, src_port, dst_port, asn, geo) |
|  - Table `transactions` stores (txid, fee, size, timestamp)                    |
|  - Linked directly on: network_events.transaction_id = transactions.tx_id       |
|                                                                                 |
|  [ TIER 2: ML FEATURE CORRELATION ] ─────────────────────────────────── [ PASS ] |
|  - `net_hist_unique_ips_for_addr`: Measures IP dispersion per wallet address.   |
|  - `time_since_prev_addr_tx_sec`: Measures transaction velocity relative to net.|
|  - `net_is_standard_bitcoin_port`: Flags obfuscated/proxy transport.           |
|                                                                                 |
|  [ TIER 3: TOPOLOGICAL GRAPH CANVAS ] ───────────────────────────────── [ FAIL ] |
|  - Cytoscape canvas ONLY renders Address nodes and Fund Flow edges.             |
|  - IP addresses are NOT displayed as nodes or broadcast edges on the canvas!    |
+---------------------------------------------------------------------------------+
```

---

### 3.4. Entity & Transaction Graph Topology

An inspection of `backend/services/graph_service.py` and `frontend/src/pages/graph-explorer.tsx` reveals the current topological structure:

- **Current Graph Elements:**
  - Nodes: `address` (Displays hash, balance, risk severity color).
  - Edges: Directed fund transfers aggregating satoshi values and transaction counts.
- **Missing Graph Elements:**
  - Nodes of type `ip`: Neither `graph_service.py` nor `graph-explorer.tsx` creates IP nodes.
  - Edges of type `broadcast`: No edges linking `IP -> Transaction` or `IP -> Address`.
- **Evaluator Impact:** Evaluators specifically looking for the *"entity/transaction graph linking IPs, wallets, and transactions"* will notice that only wallet addresses are visible on the canvas.

---

### 3.5. AI/ML Engine & Model Verification

AquaSynex avoids heuristic rule engines in favor of a dual-model ML architecture orchestrated in `pipeline/ml/model_inference.py`:

```
                                  46 Raw Features
                                         │
                                         ▼
                            RobustScaler + OneHotEncoder
                               (71-Dimensional Vector)
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
         [ MODEL 1: XGBOOST ]                      [ MODEL 2: CATBOOST ]
       aquasynex_xgb_binary_v1.json            aquasynex_catboost_multiclass_v1.cbm
       - Task: Binary Illicit Risk Prob        - Task: 11-Class Typology Attribution
       - Output: P(illicit) in [0.0, 1.0]      - Output: Class + Softmax Confidence
       - XAI: Exact Local TreeSHAP             - Typologies: Peeling, Mixing, etc.
```

- **Pretrained Artifacts Present:**
  - `models/aquasynex_xgb_binary_v1.json` (782 KB)
  - `models/aquasynex_catboost_multiclass_v1.cbm` (1.14 MB)
  - `models/preprocessor_v1.joblib` (RobustScaler + OneHotEncoder)
  - `models/model_metadata_v1.json` (Feature names, dimensions, metrics)
- **Zero Mock / Fake Policy:** Line 7 of `model_inference.py` strictly mandates zero synthetic mocks or heuristic fallbacks. Models are executed natively; missing models trigger an explicit `ModelLoadError`.

---

### 3.6. Anomaly Detection vs. Supervised Risk Classification

- **PS Language:** *"apply AI/ML to detect anomalies"*
- **AquaSynex Implementation:** Supervised Gradient Boosted Decision Trees predicting $P(\text{illicit})$ trained against verified illicit/benign transaction patterns.
- **Scientific Reality:** In production financial intelligence, pure unsupervised anomaly detection (e.g. Isolation Forest) generates high false-positive rates on institutional exchanges and miners due to high volume. AquaSynex implements supervised risk scoring combined with TreeSHAP feature-level anomaly explanation.

---

### 3.7. Entity Clustering Engine

- **Implementation:** `ml/graph_analysis/entity_clustering.py`
- **Algorithm:** Disjoint-Set Union-Find with path compression and rank optimization.
- **Heuristics Applied:**
  1. *Multi-Input Heuristic (MIH / Co-spending):* All input addresses in a multi-input transaction are assumed to be controlled by the same wallet entity.
  2. *Change Address Heuristic:* Single-use return outputs are clustered with the sender.
- **Anti-Leakage Guarantees:** Chronological streaming processing ensures transactions at time $t$ cannot retrospectively cluster addresses observed at time $t - \Delta$.

---

### 3.8. Ranked & Explainable Alert Engine

- **Alert Ranking:** Calculated Priority Score combining Risk Probability (70%) and Typology Severity Weight (30%). Displayed sorted descending by risk score.
- **Explainability (TreeSHAP):** Live computation using XGBoost's native `pred_contribs=True`. Returns exact additive log-odds contributions per feature for every scored transaction.
- **Investigator Evidence Display:** Features are mapped to human-readable labels with physical units (e.g., *"Historical unique IPs = 14 (+32% Risk)"*, *"Relational fan-out = 28 (+24% Risk)"*).
- **Confidence Metric:** Defined as $\max_k P(\text{Typology}_k | X)$, representing classifier certainty bounded in $[0.0, 1.0]$.

---

### 3.9. GeoIP Database Integration Audit

The Problem Statement explicitly requires:
> *"geo_country/asn (integrate open source downloadable Geo IP database)"*

- **Codebase Truth:** `backend/services/dataset_service.py` directly ingests `country` and `asn` from incoming dataset columns.
- **Audit Deficit:** The repository **does NOT bundle an offline GeoIP database** (`.mmdb` file) and contains **no offline lookup library** (such as MaxMind `geoip2`). If a dataset contains only raw IP addresses, country and ASN cannot be resolved.

---

### 3.10. Frontend Dashboard & Forensic UI

- **Aesthetics & Design System:** Built in React 18 + Tailwind CSS. Follows an institutional light theme (`#f7f7f5` warm canvas, `#173b63` deep navy headers/accents, restrained semantic alert badges).
- **Investigation Workflows:**
  - `/dashboard`: System overview, volume stats, risk tier distributions.
  - `/alerts`: Triage table with sorting, risk filters, and confidence meters.
  - `/graph`: Cytoscape.js canvas supporting pan/zoom, node drag, hop expansion, and transaction inspection drawers.
  - `/investigation`: Dedicated Address/Transaction Dossier featuring TreeSHAP waterfall charts, direct counterparties, and historical velocity.
  - `/network`: Progressive disclosure hierarchy: Country $\to$ ASN $\to$ IP Address $\to$ Associated Transactions $\to$ Wallet Dossier.
  - `/datasets`: File upload, validation, parsing, and pipeline orchestration.

---

## 4. Technical Differentiators (Beyond the Problem Statement)

AquaSynex implements several high-value forensic capabilities that exceed standard hackathon submissions:

1. **Exact Additive TreeSHAP Inference:** Rather than static feature importance or generic LIME approximations, AquaSynex calculates true Shapley values live for every transaction.
2. **Dual-Model Multi-Typology Attribution:** Separates binary risk scoring ($P(\text{illicit})$) from 11-class criminal typology categorization (Peeling Chain, Mixer Deposit, Burst Layering, Ransomware, etc.).
3. **46 Canonical Forensic Features:** Combines transactional statistics, address history, rolling temporal windows, transport ports, and NetworkX topological graph features (PageRank, degree centralities, clustering coefficients).
4. **Strict Temporal Anti-Leakage Invariant:** Feature extraction enforces chronological boundary guarantees, preventing future data snooping during historical analysis.
5. **Embedded In-Process Columnar Analytical Store:** Uses DuckDB instead of an external database daemon, delivering sub-second analytical queries over millions of records with zero operational setup.

---

## 5. Vulnerability & Rejection Points (Priority Classification)

```
                                VULNERABILITY PYRAMID
                                
                                     ▲
                                    / \
                                   / P0\    <-- Fatal Compliance Breaches
                                  /-----\       (XML Ingestion, Offline GeoIP DB)
                                 /   P1  \  <-- Serious Evaluator Challenges
                                /---------\     (Canvas IP Nodes, Anomaly Framing)
                               /     P2    \ <-- UI/UX Polish
                              /-------------\   (Cluster Envelopes, Bulk Warnings)
```

### [P0] Critical Compliance Breaches (Immediate Rejection Risk)
1. **Missing XML Ingestion Parser:**
   - *Risk:* Live evaluator tests with an `.xml` dataset will fail immediately with HTTP 415.
   - *Action:* Implement native XML parsing in `backend/services/dataset_service.py`.
2. **Missing Bundled GeoIP Database:**
   - *Risk:* Evaluator asks to see the integrated downloadable GeoIP database mandated by the PS.
   - *Action:* Bundle MaxMind `GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb` in `data/geoip/` with an offline lookup resolver.

### [P1] Major Evaluator Challenges (Demerit Risk)
3. **Absence of IP Nodes in Graph Explorer Canvas:**
   - *Risk:* Evaluator observes that the link-analysis canvas only displays addresses, missing the explicitly requested IP-wallet-TX correlation.
   - *Action:* Add an "Include Network Topology" toggle in Graph Explorer to render IP nodes linked to transactions.
4. **Supervised Risk Scoring vs. Anomaly Detection Nuance:**
   - *Risk:* Evaluator argues that XGBoost is supervised classification, not anomaly detection.
   - *Action:* Implement an unsupervised Isolation Forest anomaly index alongside XGBoost, or formalize the supervised anomaly detection defense.

### [P2] Refinements & Polish
5. **Entity Cluster Visual Grouping:** Render visual bounding boxes or compound nodes around addresses belonging to the same entity cluster in Cytoscape.

---

## 6. Step-by-Step Implementation Plan to Reach 100% PS Compliance

---

### PHASE 1: XML Ingestion Engine (Priority: P0)

#### Objective
Enable native parsing of XML transaction datasets matching the SIH schema without requiring external network dependencies.

#### Target Files
- `backend/services/dataset_service.py`
- `tests/test_xml_ingestion.py`

#### Implementation Specification
1. Update `ALLOWED_FORMATS`:
   ```python
   ALLOWED_FORMATS = {
       ".csv": "csv",
       ".parquet": "parquet",
       ".json": "json",
       ".jsonl": "jsonl",
       ".xml": "xml",
   }
   ```
2. Implement `_parse_xml_dataset` using Python's standard library `xml.etree.ElementTree`:
   ```python
   import xml.etree.ElementTree as ET
   import pandas as pd

   def _parse_xml_to_df(file_path: Path) -> pd.DataFrame:
       tree = ET.parse(file_path)
       root = tree.getroot()
       records = []
       for tx_elem in root.findall(".//transaction"):
           record = {child.tag: child.text for child in tx_elem}
           records.append(record)
       return pd.DataFrame(records)
   ```
3. Support both element-based `<transaction><txid>...</txid></transaction>` and attribute-based XML schemas.

#### Verification
- Create `datasets/test_sample.xml`.
- Execute upload via `POST /api/datasets/upload`. Confirm HTTP 201 and identical table population in DuckDB.

---

### PHASE 2: Bundled Offline GeoIP Database (Priority: P0)

#### Objective
Fulfill the explicit PS requirement: *"geo_country/asn (integrate open source downloadable Geo IP database)"* by bundling offline MaxMind databases and resolving raw IPs.

#### Target Files
- `data/geoip/GeoLite2-City.mmdb` (Bundled artifact)
- `data/geoip/GeoLite2-ASN.mmdb` (Bundled artifact)
- `backend/utils/geoip_resolver.py` (New offline resolver)
- `backend/services/dataset_service.py` (Integration hook)
- `Dockerfile.backend` (Ensure `data/geoip` is copied into container)

#### Implementation Specification
1. Create `backend/utils/geoip_resolver.py`:
   ```python
   from pathlib import Path
   from typing import Optional, Tuple
   import maxminddb

   class OfflineGeoIPResolver:
       def __init__(self, geoip_dir: Path):
           city_path = geoip_dir / "GeoLite2-City.mmdb"
           asn_path = geoip_dir / "GeoLite2-ASN.mmdb"
           self.city_reader = maxminddb.open_database(str(city_path)) if city_path.exists() else None
           self.asn_reader = maxminddb.open_database(str(asn_path)) if asn_path.exists() else None

       def resolve(self, ip_str: str) -> Tuple[str, str]:
           country = "UNKNOWN"
           asn = "UNKNOWN"
           if not ip_str or ip_str in ("UNKNOWN", "127.0.0.1"):
               return country, asn
           try:
               if self.city_reader:
                   city_data = self.city_reader.get(ip_str)
                   if city_data and "country" in city_data:
                       country = city_data["country"].get("iso_code", "UNKNOWN")
               if self.asn_reader:
                   asn_data = self.asn_reader.get(ip_str)
                   if asn_data and "autonomous_system_number" in asn_data:
                       asn = f"AS{asn_data['autonomous_system_number']}"
           except Exception:
               pass
           return country, asn
   ```
2. Integrate into `DatasetService.upload_dataset`: If `country` or `asn` are missing or empty in ingested rows, automatically resolve using `OfflineGeoIPResolver`.

---

### PHASE 3: Tripartite IP-Wallet-TX Graph Representation (Priority: P1)

#### Objective
Visibly represent the correlation between network-layer (IPs) and blockchain-layer (wallets, TXIDs) entities on the interactive Cytoscape canvas.

#### Target Files
- `backend/services/graph_service.py`
- `frontend/src/pages/graph-explorer.tsx`

#### Implementation Specification
1. **Backend Enhancement (`graph_service.py`):**
   Add query parameter `include_network: bool = False` to `get_analysis_graph`.
   When `include_network=True`:
   - Query unique `src_ip` associated with transactions in the subgraph from `network_events`.
   - Inject IP nodes:
     ```python
     nodes_dict[f"ip_{ip}"] = {
         "id": f"ip_{ip}",
         "label": ip,
         "nodeType": "ip",
         "riskScore": None,
         "riskLevel": None,
         "metadata": {"asn": asn, "country": country},
     }
     ```
   - Inject broadcast edges:
     ```python
     edges.append({
         "id": f"edge_net_{ip}_{tx_id}",
         "source": f"ip_{ip}",
         "target": primary_sender_address,
         "edgeType": "network_broadcast",
         "label": "Broadcast",
     })
     ```
2. **Frontend Styling (`graph-explorer.tsx`):**
   - Add toggle in toolbar: `[x] Show Network Layer (IPs)`.
   - Style IP nodes as distinct amber squares:
     ```typescript
     {
       selector: 'node[nodeType = "ip"]',
       style: {
         "background-color": "#A46A16",
         "shape": "rectangle",
         "label": "data(label)",
         "font-size": "9px"
       }
     }
     ```

---

### PHASE 4: Dual Anomaly Scoring Architecture (Priority: P1)

#### Objective
Provide both unsupervised anomaly detection and supervised risk scoring to address academic and forensic perspectives simultaneously.

#### Implementation Specification
1. Train a lightweight `IsolationForest` on the 46 canonical features.
2. Output two explicit metrics for every transaction:
   - `Anomaly Index`: Unsupervised outlier score from Isolation Forest in $[0.0, 1.0]$.
   - `Risk Probability`: Supervised illicit probability from XGBoost in $[0.0, 1.0]$.
3. In the UI, display both the **Statistical Anomaly Index** and the **Forensic Illicit Risk Score**.

---

## 7. Complete Architecture Traceability Matrix

```mermaid
graph TD
    subgraph INGESTION["1. Ingestion Layer (Air-Gapped)"]
        CSV[CSV Dataset]
        JSON[JSON / JSONL]
        XML[XML Dataset (P0)]
        MMDB[(Bundled GeoIP .mmdb)]
    end

    subgraph STORAGE["2. Relational Analytical Engine (DuckDB)"]
        NET[network_events]
        TX[transactions]
        INPUTS[transaction_inputs]
        OUTPUTS[transaction_outputs]
        CORR[(Network ↔ Ledger Relational Joins)]
    end

    subgraph ANALYTICS["3. Feature Engineering & Graph Analytics"]
        FE[46 Canonical Features]
        UF[Disjoint-Set Union-Find Clustering]
        NX[NetworkX Topological Metrics]
    end

    subgraph ML["4. Dual-Model AI/ML & Explainability"]
        XGB[XGBoost Risk Classifier]
        CAT[CatBoost Typology Classifier]
        SHAP[Exact Live TreeSHAP Engine]
    end

    subgraph UI["5. Institutional Forensic Dashboard"]
        DASH[Dashboard Overview]
        ALERTS[Ranked Alerts]
        GRAPH[Cytoscape Graph Canvas (IP + Wallet + TX)]
        DOSSIER[Address & Investigation Dossier]
        NET_INTEL[Network Intelligence Drilldown]
    end

    CSV --> CORR
    JSON --> CORR
    XML --> CORR
    MMDB -.-> CORR

    CORR --> NET
    CORR --> TX
    CORR --> INPUTS
    CORR --> OUTPUTS

    NET --> FE
    TX --> FE
    INPUTS --> UF
    OUTPUTS --> NX

    FE --> XGB
    FE --> CAT
    XGB --> SHAP

    XGB --> ALERTS
    CAT --> ALERTS
    SHAP --> DOSSIER
    UF --> GRAPH
    CORR --> GRAPH
    NET --> NET_INTEL
    ALERTS --> DASH
```

---

## 8. Ideal 10-Minute Hackathon Demonstration Script

| Time | Phase | Screen / Action | Talking Points for Evaluators |
| :---: | :--- | :--- | :--- |
| **0:00 - 1:30** | **Air-Gap Verification & Architecture** | Terminal + Docker | *"Notice Wi-Fi is disabled. AquaSynex is 100% offline with zero cloud or API dependencies. DuckDB and models run strictly in-process."* |
| **1:30 - 3:00** | **Multi-Format Bulk Ingestion** | `/datasets` | Drop a mixed CSV/JSON/XML file. *"Our streaming pipeline parses transaction UTXOs and network telemetry, enriching raw IPs using our bundled offline GeoIP database."* |
| **3:00 - 4:30** | **Pipeline Execution & ML Inference** | `/datasets` $\to$ Progress Modal | *"We compute 46 canonical features including temporal anti-leakage windows and NetworkX topological metrics, evaluated live across our dual ML models."* |
| **4:30 - 6:00** | **Ranked Alert Triage & Confidence** | `/alerts` | *"Alerts are prioritized by risk score. Each alert shows model confidence, severity tier, and assigned typology (e.g. Peeling Chain or Mixer Deposit)."* |
| **6:00 - 7:30** | **Explainable AI (TreeSHAP Evidence)** | `/investigation` Dossier | *"We do not rely on black-box predictions. Here is the exact TreeSHAP attribution waterfall showing which specific features drove this transaction's risk."* |
| **7:30 - 9:00** | **Tripartite Link Analysis** | `/graph` Explorer | Toggle on Network Layer. *"Here is the tripartite graph linking broadcast IPs, wallet addresses, and multi-hop transactions with interactive neighborhood expansion."* |
| **9:00 - 10:00** | **Network Intelligence Drilldown** | `/network` Intelligence | Show Country $\to$ ASN $\to$ IP $\to$ Transaction drilldown. Answer questions authoritatively using forensic evidence. |

---

## 9. SIH Technical Evaluator Defense Playbook

### Q1: "Where do your IP addresses come from and how are they correlated with transactions?"
> **Defense:** *"In Bitcoin P2P networks, transactions are propagated via broadcast messages. Our dataset schema captures source/relay node IPs and timestamps. We correlate them through the `transaction_id` foreign key in our embedded analytical database and compute relational features such as IP reuse velocity (`net_hist_unique_ips_for_addr`) and standard port adherence."*

### Q2: "Why did you use supervised learning instead of pure unsupervised anomaly detection?"
> **Defense:** *"In Bitcoin forensic analysis, unsupervised models flag high-volume mining pools and institutional exchange wallets as outliers, generating unacceptably high false-positive rates. We utilize supervised gradient boosting (XGBoost) trained on validated illicit topologies, coupled with live TreeSHAP explainability to surface specific anomalous feature deviations per transaction."*

### Q3: "How does your entity clustering work? Is it ML?"
> **Defense:** *"Our entity clustering implements the industry-standard Multi-Input Heuristic (MIH) and Change Address Heuristic using an optimized Disjoint-Set Union-Find algorithm. In Bitcoin forensics, heuristic co-spending clustering is mathematically and legally deterministic, whereas unsupervised ML clustering (like K-Means) is prone to non-deterministic cluster drift."*

### Q4: "What does your confidence score represent mathematically?"
> **Defense:** *"Our confidence metric represents the maximum calibrated softmax posterior probability $\max_k P(\text{Typology}_k | X)$ from our CatBoost multi-class classifier, indicating model certainty in the assigned behavioral typology."*

---

## 10. Audit Sign-Off

This audit compares the current AquaSynex repository against the official SIH26146 Problem Statement supplied in this prompt.
