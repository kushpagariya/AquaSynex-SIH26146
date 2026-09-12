# Backend ↔ ML Contract

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This document defines the interface between the Backend layer and the ML pipeline.
> Both the Backend Owner and ML Owner must agree on this contract.
> Changing it requires both owners' approval.

---

## 1. Interface Style

The ML pipeline runs **within the backend process** as Python module imports (no separate service, no network calls). The backend invokes the ML pipeline as a Python function call.

```python
# In backend orchestration code
from pipeline.ml.model_inference import run_analysis

results: list[MLResult] = run_analysis(
    dataset_id=dataset_id,
    model_id=model_id,
    model_version=model_version,
    config=analysis_config,
    db_path=settings.DB_PATH,
    data_dir=settings.DATA_DIR,
    models_dir=settings.MODELS_DIR,
)
```

---

## 2. Function Contract

### Entry Point

```python
def run_analysis(
    dataset_id: str,
    model_id: str,
    model_version: str,
    config: AnalysisConfig,
    db_path: str,
    data_dir: str,
    models_dir: str,
) -> list[MLResult]:
    """
    Run the complete analysis pipeline for a dataset.
    
    Args:
        dataset_id:     UUID of the dataset to analyze (must exist in DuckDB)
        model_id:       ID of the ML model to use
        model_version:  Version of the ML model
        config:         Analysis configuration
        db_path:        Path to DuckDB database file
        data_dir:       Path to dataset files directory
        models_dir:     Path to model artifacts directory
    
    Returns:
        List of MLResult objects, one per analyzed entity.
    
    Raises:
        DatasetError:               Dataset not found or cannot be loaded
        ModelLoadError:             Model artifact cannot be loaded
        InvalidFeaturesError:       Feature schema mismatch
        FeatureSchemaMismatchError: Feature schema version incompatibility
        GraphError:                 Graph construction failed
        MLError:                    General ML pipeline failure
    """
```

### AnalysisConfig

```python
class AnalysisConfig:
    max_entities: int = 10000          # Limit analysis to top N entities
    top_explanations: int = 5          # Max SHAP explanations per entity
    compute_graph: bool = True         # Whether to build and use graph features
    graph_max_nodes: int = 100000      # Limit graph to N nodes
    random_state: int = 42             # For reproducibility
```

---

## 3. Return Value

The function returns `List[MLResult]`. Each `MLResult` must conform to [model-output-contract.md](../ml/model-output-contract.md).

The backend iterates over the results and:
1. Validates each `MLResult` against the contract schema.
2. Writes each result to the `ml_results` DuckDB table.
3. Updates the `analysis_runs` record with `status = 'completed'` and summary counts.

---

## 4. Error Handling

The backend wraps the `run_analysis()` call in a try/except block:

```python
try:
    results = run_analysis(...)
    # Persist results to DuckDB
    # Update analysis status to 'completed'
except DatasetError as e:
    # Update analysis status to 'failed'
    # Return DATASET_ERROR to API caller
except ModelLoadError as e:
    # Return MODEL_LOAD_ERROR
except InvalidFeaturesError as e:
    # Return INVALID_FEATURES
except FeatureSchemaMismatchError as e:
    # Return FEATURE_SCHEMA_MISMATCH
except GraphError as e:
    # Return GRAPH_ERROR
except Exception as e:
    # Return ML_ERROR (unexpected)
```

All exceptions must be catchable — the ML pipeline must not call `sys.exit()` or raise non-exception objects.

---

## 5. Asynchronous Execution

The analysis runs **asynchronously** relative to the API request. The flow is:

```
POST /api/datasets/{id}/analyses
    │
    ├── Backend validates request
    ├── Creates analysis_run record with status='pending'
    ├── Returns 202 Accepted with analysisId
    │
    └── [Background task / thread]
            ├── Updates status to 'running'
            ├── Calls run_analysis(...)
            ├── Persists results to DuckDB
            └── Updates status to 'completed' or 'failed'
```

The frontend polls `GET /api/analyses/{analysisId}` to check status.

**Implementation**: Use FastAPI `BackgroundTasks` or a thread pool. `DECISION REQUIRED` on exact async mechanism.

---

## 6. What the Backend Provides to the ML Pipeline

| Resource | How Provided |
|---|---|
| Dataset canonical records | DuckDB/Parquet at `db_path` and `data_dir` |
| Model artifacts | Files in `models_dir/{model_id}/{model_version}/` |
| Analysis configuration | `AnalysisConfig` object |
| Dataset metadata | Queryable from DuckDB `datasets` table |

---

## 7. What the ML Pipeline Must NOT Do

| Forbidden | Alternative |
|---|---|
| Modify `analysis_runs` table directly | Return results; backend updates the table |
| Call FastAPI routes | Return values to backend |
| Access `frontend/` code | Frontend has no ML code |
| Make HTTP calls | Offline system |
| Print to stdout/stderr unstructured | Use Python `logging` module |

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner + ML Owner (joint)*
*References: [model-output-contract.md](../ml/model-output-contract.md) | [error-handling.md](./error-handling.md)*
