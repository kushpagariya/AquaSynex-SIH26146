# Risk Scoring

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `DECISION REQUIRED` — The exact formula is proposed below but requires team approval before implementation.

---

## 1. What Risk Score Means

The risk score is a **calibrated analytical prioritization signal** in the range `[0.0, 1.0]`.

It represents the system's assessment of how suspicious an entity's behavioral patterns are, based on:
- Statistical deviation from the dataset population (anomaly detection)
- Feature patterns associated with known suspicious behavior (if classification is used)
- Graph topology evidence (centrality, cluster membership, etc.)

**A risk score is NOT**:
- Legal evidence of criminal activity
- A ground-truth determination of guilt
- A guarantee of suspicious activity
- Deterministic — it changes if the model, dataset, or features change

> **This must be clearly communicated to the investigator in the UI.**

---

## 2. Risk Score Range and Levels

| Risk Level | Score Range | Investigative Guidance |
|---|---|---|
| `low` | [0.0, 0.39] | Normal behavior; low priority for investigation |
| `medium` | [0.40, 0.69] | Some unusual signals; warrants attention |
| `high` | [0.70, 0.89] | Multiple significant risk indicators; investigate further |
| `critical` | [0.90, 1.00] | Highly anomalous behavior; highest investigation priority |

> **`DECISION REQUIRED`**: These threshold values are proposed defaults. They should be validated against a labeled dataset and adjusted based on precision/recall tradeoffs appropriate for the investigation context.

---

## 3. Proposed Risk Score Formula

> **`DECISION REQUIRED`**: The formula below is a proposed composite approach. Team approval is required before implementation.

### Proposed Composite Formula

```
risk_score = w_model × anomaly_score 
           + w_graph  × normalized_graph_score
           + w_behavior × normalized_behavior_score
```

Where:
- `anomaly_score` — normalized ML model output [0.0, 1.0]
- `normalized_graph_score` — composite graph centrality signal [0.0, 1.0]
- `normalized_behavior_score` — behavioral feature signal [0.0, 1.0]
- `w_model + w_graph + w_behavior = 1.0`

**Proposed initial weights** (`DECISION REQUIRED`):

| Component | Weight | Rationale |
|---|---|---|
| `w_model` | 0.60 | ML model has learned behavioral patterns |
| `w_graph` | 0.25 | Graph topology provides structural evidence |
| `w_behavior` | 0.15 | Behavioral features (velocity, size) provide direct signal |

### Alternative: Direct ML Probability

If the model directly outputs a well-calibrated probability (e.g., XGBoost with Platt scaling), then:

```
risk_score = model_probability
```

In this case, graph and behavioral signals are captured as model features, not added post-hoc.

**Preferred approach**: `DECISION REQUIRED` — The composite formula gives more interpretability; the direct probability approach is simpler and avoids double-counting.

---

## 4. Normalization of Sub-Scores

### Graph Score Normalization

The graph score is derived from graph features:

```python
# Proposed approach
graph_score = (
    alpha × normalized_pagerank
    + beta  × normalized_weighted_degree
    + gamma × normalized_component_size
)
# alpha + beta + gamma = 1.0
```

Where each component is normalized to [0.0, 1.0] relative to the dataset.

`DECISION REQUIRED`: α, β, γ weights need validation.

### Behavior Score Normalization

The behavior score captures non-graph behavioral signals:

```python
behavior_score = (
    sigmoid(z_score(addr_tx_per_day))       # Velocity
    × sigmoid(z_score(addr_transaction_count))
)
```

`DECISION REQUIRED`: Exact formula requires dataset validation.

---

## 5. Score Calibration

**What is calibration?**

A calibrated score means `risk_score = 0.80` implies approximately 80% of entities with that score are actually anomalous (in a supervised setting). Without calibration, the score is a ranking signal, not a probability.

**For unsupervised models (Phase 1)**: Calibration cannot be validated without labels. The score is a relative ranking signal only.

**For supervised models (Phase 2)**: Use Platt Scaling or Isotonic Regression to calibrate probabilities.

`DECISION REQUIRED`: Whether to calibrate and the calibration method.

---

## 6. Threshold Selection

**Recommended process** (when labeled data is available):

1. Plot Precision-Recall curve.
2. Choose threshold that maximizes F1 or achieves acceptable precision at target recall.
3. Validate threshold on held-out dataset.
4. Document chosen threshold in model metadata.

**Without labeled data**: Default thresholds from Section 2 are used. Investigators should treat the risk levels as relative rankings.

---

## 7. What the Risk Score Does NOT Account For

| Factor | Status |
|---|---|
| Legal jurisdiction | Out of scope |
| Transaction context (e.g., exchange vs. individual) | Not modeled directly |
| Real-time blockchain changes after dataset cutoff | Out of scope (offline system) |
| False positive burden on innocent entities | Must be communicated to investigator |
| Model drift over time | `FUTURE` consideration |

---

## 8. Investigator Guidance

The UI must communicate the following to investigators:

1. Risk score is a **relative prioritization signal** — compare entities within the same dataset.
2. Low risk score does not mean clean — it means not anomalous relative to this dataset.
3. High risk score does not mean guilty — it requires investigator judgment and corroboration.
4. The contributing features are visible in the explanation view.

---

*Last updated: 2026-09-11 | Status: DECISION REQUIRED | Owner: ML Owner + Backend Owner*
*References: [anomaly-detection.md](./anomaly-detection.md) | [model-output-contract.md](./model-output-contract.md) | [explainability.md](./explainability.md)*
