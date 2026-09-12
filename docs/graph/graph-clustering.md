# Entity Clustering & Address Linking Specification (Phase 2.4)

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Authoritative Specification**: Defines the heuristics, streaming Union-Find data structure, neutral terminology standards, and temporal anti-leakage invariants for entity clustering in AquaSynex.

**Status**: `IMPLEMENTED`

---

## 1. Algorithmic Principles & Heuristics

Bitcoin's pseudonymous UTXO accounting model allows entities to generate arbitrary numbers of addresses. AquaSynex implements two standard blockchain link-analysis heuristics:

### 1.1. Multi-Input (Common Spending) Heuristic
- **Theoretical Basis**: In a standard Bitcoin transaction, all input UTXOs must be signed by private keys possessed or coordinated by the same entity.
- **Rule**: If a transaction $T$ contains multiple distinct input addresses $\{A_1, A_2, \dots, A_k\}$, all addresses are inferred to belong to the same behavioral cluster.
- **Limitation / Caveat**: Collaborative transactions (e.g. CoinJoin) violate this heuristic by combining unrelated inputs. In our canonical dataset, standard UTXO spending applies.

### 1.2. Change Address Heuristic
- **Theoretical Basis**: When a UTXO is spent, remaining value is directed to a newly generated change address owned by the sender.
- **Rule**: If an output address is identified as a change address (`is_change == True`), it is linked to the sender's input cluster.

---

## 2. Streaming Chronological Processing & Temporal Anti-Leakage

Entity clustering must NOT be computed globally across the entire dataset before feature extraction. A retrospective Union-Find causes **future-to-past leakage**, where an address cluster appears large and active early in history before the merging transactions actually took place.

### The Strict Streaming State Machine:
For each transaction $T_i$ in ascending chronological order:
1. **Historical Feature Extraction ($t < T_i$)**:
   - Query the Union-Find structure using the primary input address.
   - Record `hist_cluster_id`, `hist_cluster_size`, and `hist_cluster_tx_count` *as they exist prior to $T_i$*.
2. **Multi-Input Union**:
   - If $k \ge 2$ inputs are present, union their disjoint sets.
3. **Change Output Union**:
   - Union any identified change address outputs into the active input cluster.
4. **Activity Update**:
   - Increment the transaction counter for the merged cluster root.

### Future Invariance Guarantee:
Appending subsequent transactions at timestamp $t > T_i$ never alters the cluster features computed for $T_i$.

---

## 3. Neutral Terminology Mandate

Heuristic link analysis clusters addresses based solely on structural graph topology. They do not constitute legal proof or identity verification.

All technical documentation, code comments, UI labels, and investigative reports must adhere to the following standards:

| Approved Neutral Terminology | Prohibited Biased Terminology | Rationale |
|---|---|---|
| **Inferred Behavioral Cluster** | Real-world Identity / Owner | Graph heuristics infer co-control patterns, not legal identities. |
| **Address Cluster** | Criminal Wallet / Suspect Entity | Addresses may be shared, custodial, or third-party services. |
| **Co-spending Association** | Proof of Collusion | Multi-input signatures can originate from multisig or aggregators. |
| **Statistical Risk Score** | Guilt Score / Fraud Probability | ML scores quantify pattern deviations, not legal culpability. |

---

## 4. Union-Find Disjoint-Set Implementation

The clustering engine is implemented in `ml/graph_analysis/entity_clustering.py` using a Disjoint-Set (Union-Find) structure optimized with:
- **Path Compression**: $O(\alpha(N))$ nearly linear amortized lookup.
- **Union by Rank**: Balances tree height during large cluster merges.
- **Augmented Member Sets**: Dynamically tracks set cardinality (`cluster_size`) and transaction frequency (`cluster_tx_count`).

---

*Last updated: 2026-09-12 | Status: IMPLEMENTED | Owner: ML Owner (Graph)*
