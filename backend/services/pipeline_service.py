"""ML Pipeline integration adapter and contract boundary.

Authoritative reference: docs/backend/backend-ml-contract.md and docs/ml/model-output-contract.md
Rules:
- Establish clean integration boundary for ML
- Consume List[MLResult] conforming to model-output-contract.md
- Never fabricate fake predictions
- Validate results before persisting to DuckDB ml_results table
"""

from datetime import datetime, timezone
import importlib
from typing import Any, Callable, Dict, List, Optional
import uuid
import duckdb
from backend.config import settings
from backend.db.connection import get_db_lock
from backend.db.queries import results as result_queries
from backend.schemas.analyses import AnalysisConfigSchema
from backend.utils.errors import (
    FeatureSchemaMismatchError,
    InvalidFeaturesError,
    MLError,
    ModelLoadError,
)
from backend.utils.logging import logger

_custom_runner: Optional[Callable[..., List[Dict[str, Any]]]] = None


def set_pipeline_runner(runner_fn: Optional[Callable[..., List[Dict[str, Any]]]]) -> None:
    """Set custom ML pipeline runner callable (primarily for testing and mock injection)."""
    global _custom_runner
    _custom_runner = runner_fn


def reset_pipeline_runner() -> None:
    """Reset custom runner to standard import mechanism."""
    global _custom_runner
    _custom_runner = None


class PipelineService:
    """Adapter bridging the Backend and the ML Subsystem."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def run_analysis(
        self,
        dataset_id: str,
        analysis_id: str,
        model_id: str,
        model_version: str,
        config: AnalysisConfigSchema,
    ) -> List[Dict[str, Any]]:
        """Invoke ML pipeline and persist results to DuckDB.

        Calls `pipeline.ml.model_inference.run_analysis(...)` as specified in docs/backend/backend-ml-contract.md.
        If external ML module or model artifact is unavailable, raises ModelLoadError.
        Never fabricates heuristics or fake predictions inside the backend.
        """
        logger.info(
            f"Invoking ML analysis for dataset {dataset_id} with model {model_id} (v{model_version})"
        )

        global _custom_runner
        ml_results: List[Dict[str, Any]] = []

        if _custom_runner is not None:
            raw_results = _custom_runner(
                dataset_id=dataset_id,
                model_id=model_id,
                model_version=model_version,
                config=config,
                db_path=settings.DB_PATH,
                data_dir=settings.DATA_DIR,
                models_dir=settings.MODELS_DIR,
            )
            ml_results = [r if isinstance(r, dict) else r.dict() for r in raw_results]
        else:
            try:
                pipeline_mod = importlib.import_module("pipeline.ml.model_inference")
                run_func = getattr(pipeline_mod, "run_analysis")
                raw_results = run_func(
                    dataset_id=dataset_id,
                    model_id=model_id,
                    model_version=model_version,
                    config=config,
                    db_path=settings.DB_PATH,
                    data_dir=settings.DATA_DIR,
                    models_dir=settings.MODELS_DIR,
                )
                ml_results = [r if isinstance(r, dict) else r.dict() for r in raw_results]
            except ModuleNotFoundError as exc:
                logger.error(
                    f"ML pipeline module 'pipeline.ml.model_inference' is not installed: {exc}"
                )
                raise ModelLoadError(
                    f"ML pipeline module 'pipeline.ml.model_inference' is not installed or model '{model_id}' artifact is unavailable",
                    details={"modelId": model_id, "modelVersion": model_version, "error": str(exc)},
                ) from exc
            except (ModelLoadError, InvalidFeaturesError, FeatureSchemaMismatchError):
                raise
            except Exception as exc:
                logger.error(f"ML Pipeline execution failed: {exc}")
                raise MLError(f"ML pipeline execution error: {exc}") from exc

        # 1. Validate all items before persisting any item
        for item in ml_results:
            self._validate_ml_result(item)

        # 2. Persist in a database transaction with rollback on failure
        with get_db_lock():
            self.conn.execute("BEGIN TRANSACTION")
            try:
                for item in ml_results:
                    self._persist_result(dataset_id, analysis_id, model_id, model_version, item)
                self.conn.execute("COMMIT")
                try:
                    self.conn.execute("CHECKPOINT")
                except Exception:
                    pass
            except Exception as exc:
                self.conn.execute("ROLLBACK")
                logger.error(f"Failed to persist ML results for analysis {analysis_id}: {exc}")
                raise MLError(f"Failed to persist ML results: {exc}") from exc

        logger.info(f"Persisted {len(ml_results)} ML results for analysis {analysis_id}")
        return ml_results

    def _as_score(self, name: str, value: Any, required: bool = True) -> Optional[float]:
        """Safely convert and validate a score between 0.0 and 1.0, raising MLError on failure."""
        if value is None:
            if required:
                raise MLError(f"MLResult invariant violation: '{name}' is required")
            return None

        try:
            val = float(value)
        except (ValueError, TypeError) as exc:
            raise MLError(
                f"MLResult invariant violation: '{name}' must be numeric, got {value}"
            ) from exc

        if not (0.0 <= val <= 1.0):
            raise MLError(
                f"MLResult invariant violation: '{name}' must be between 0.0 and 1.0, got {val}"
            )
        return val

    def _validate_ml_result(self, result: Dict[str, Any]) -> None:
        """Validate that an MLResult item conforms to the documented ML contract."""
        entity_id = result.get("entity_id")
        if not entity_id or not isinstance(entity_id, str):
            raise MLError("MLResult invariant violation: 'entity_id' must be a non-empty string")

        entity_type = result.get("entity_type")
        if entity_type not in ("transaction", "address"):
            raise MLError(
                f"MLResult invariant violation: 'entity_type' must be 'transaction' or 'address', got '{entity_type}'"
            )

        self._as_score("anomaly_score", result.get("anomaly_score"), required=True)
        self._as_score("risk_score", result.get("risk_score"), required=True)

        risk_level = result.get("risk_level")
        if risk_level not in ("low", "medium", "high", "critical"):
            raise MLError(
                f"MLResult invariant violation: 'risk_level' must be one of low/medium/high/critical, got '{risk_level}'"
            )

        self._as_score("confidence", result.get("confidence"), required=False)

    def _persist_result(
        self,
        dataset_id: str,
        analysis_id: str,
        model_id: str,
        model_version: str,
        result: Dict[str, Any],
    ) -> None:
        """Write single validated MLResult to DuckDB."""
        result_id = str(uuid.uuid4())
        result_queries.insert_ml_result(
            conn=self.conn,
            result_id=result_id,
            analysis_id=analysis_id,
            dataset_id=dataset_id,
            entity_id=result["entity_id"],
            entity_type=result["entity_type"],
            anomaly_score=float(result.get("anomaly_score", 0.0)),
            risk_score=float(result.get("risk_score", 0.0)),
            risk_level=str(result.get("risk_level", "low")),
            model_id=model_id,
            model_version=model_version,
            prediction_label=result.get("prediction_label"),
            confidence=result.get("confidence"),
            explanation_json=result.get("explanations", []),
            features_json=result.get("features", []),
            graph_evidence_json=result.get("graph_evidence", []),
            predicted_at=result.get("predicted_at"),
        )
