"""Analysis orchestration service managing asynchronous runs and summary counts."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from fastapi import BackgroundTasks
import duckdb
from backend.config import settings
from backend.db.connection import get_db_lock
from backend.db.queries import analyses as analysis_queries
from backend.db.queries import datasets as dataset_queries
from backend.schemas.analyses import AnalysisConfigSchema
from backend.services.pipeline_service import PipelineService
from backend.utils.errors import (
    DatasetAnalysisRunningError,
    DatasetError,
    DatasetNotFoundError,
    DatasetProcessingError,
    ModelNotFoundError,
)
from backend.utils.logging import logger


class AnalysisService:
    """Orchestrates analysis runs, background task execution, and result aggregation."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.pipeline_service = PipelineService(conn)

    def trigger_analysis(
        self,
        dataset_id: str,
        model_id: Optional[str] = None,
        model_version: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, Any]:
        """Trigger an asynchronous analysis run on a dataset."""
        # Check dataset status
        dataset = dataset_queries.get_dataset_by_id(self.conn, dataset_id)
        if dataset["status"] == "processing":
            raise DatasetProcessingError(
                f"Dataset '{dataset_id}' is still being processed",
                details={"datasetId": dataset_id, "status": dataset["status"]},
            )
        if dataset["status"] == "error":
            raise DatasetError(
                f"Dataset '{dataset_id}' is in error state: {dataset.get('error_message')}",
                details={"datasetId": dataset_id, "status": dataset["status"]},
            )

        # Check if an analysis is already running or pending on this dataset
        running_res = self.conn.execute(
            "SELECT COUNT(*) FROM analysis_runs WHERE dataset_id = ? AND status IN ('pending', 'running')",
            [dataset_id],
        ).fetchone()
        if running_res and running_res[0] > 0:
            raise DatasetAnalysisRunningError(
                f"An analysis is already running or pending on dataset '{dataset_id}'",
                details={"datasetId": dataset_id},
            )

        chosen_model_id = model_id or settings.DEFAULT_MODEL_ID
        chosen_model_version = model_version or settings.DEFAULT_MODEL_VERSION

        # Validate model_id against registered models / model directories
        valid_models = {settings.DEFAULT_MODEL_ID}
        models_dir = Path(settings.MODELS_DIR)
        if models_dir.exists():
            for p in models_dir.iterdir():
                if p.is_dir():
                    valid_models.add(p.name)

        if chosen_model_id not in valid_models:
            raise ModelNotFoundError(model_id=chosen_model_id, version=chosen_model_version)

        analysis_id = str(uuid.uuid4())
        config_obj = AnalysisConfigSchema(**(config_dict or {}))

        # Insert analysis record with status='pending' under lock
        with get_db_lock():
            analysis_queries.insert_analysis_run(
                conn=self.conn,
                analysis_id=analysis_id,
                dataset_id=dataset_id,
                status="pending",
                model_id=chosen_model_id,
                model_version=chosen_model_version,
                config=config_obj.model_dump(),
                started_at=datetime.now(timezone.utc),
            )

        # Launch background execution
        if background_tasks is not None:
            background_tasks.add_task(
                self._execute_analysis_run,
                analysis_id=analysis_id,
                dataset_id=dataset_id,
                model_id=chosen_model_id,
                model_version=chosen_model_version,
                config=config_obj,
            )
        else:
            # Fallback for sync or direct invocation (e.g. tests)
            self._execute_analysis_run(
                analysis_id=analysis_id,
                dataset_id=dataset_id,
                model_id=chosen_model_id,
                model_version=chosen_model_version,
                config=config_obj,
            )

        return analysis_queries.get_analysis_by_id(self.conn, analysis_id)

    def _execute_analysis_run(
        self,
        analysis_id: str,
        dataset_id: str,
        model_id: str,
        model_version: str,
        config: AnalysisConfigSchema,
    ) -> None:
        """Background worker executing ML analysis and calculating summary risk stats."""
        try:
            logger.info(f"Starting analysis run {analysis_id}...")
            with get_db_lock():
                analysis_queries.update_analysis_status(self.conn, analysis_id, status="running")

            # Run ML analysis
            results = self.pipeline_service.run_analysis(
                dataset_id=dataset_id,
                analysis_id=analysis_id,
                model_id=model_id,
                model_version=model_version,
                config=config,
            )

            # Calculate entity counts and risk metrics
            entity_count = len(results)
            high_risk_count = sum(1 for r in results if 0.70 <= float(r.get("risk_score", 0.0)) < 0.90)
            critical_risk_count = sum(1 for r in results if float(r.get("risk_score", 0.0)) >= 0.90)

            # Update status to completed
            with get_db_lock():
                analysis_queries.update_analysis_status(
                    conn=self.conn,
                    analysis_id=analysis_id,
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                    entity_count=entity_count,
                    high_risk_count=high_risk_count,
                    critical_risk_count=critical_risk_count,
                )
            logger.info(
                f"Analysis run {analysis_id} completed successfully. Entities: {entity_count}, High: {high_risk_count}, Critical: {critical_risk_count}"
            )
        except Exception as exc:
            logger.error(f"Analysis run {analysis_id} failed: {exc}")
            with get_db_lock():
                analysis_queries.update_analysis_status(
                    conn=self.conn,
                    analysis_id=analysis_id,
                    status="failed",
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(exc),
                )

    def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Get status and details of an analysis run."""
        return analysis_queries.get_analysis_by_id(self.conn, analysis_id)

    def list_analyses_for_dataset(self, dataset_id: str) -> List[Dict[str, Any]]:
        """List all analysis runs for a dataset."""
        # Ensure dataset exists
        dataset_queries.get_dataset_by_id(self.conn, dataset_id)
        return analysis_queries.list_analyses_for_dataset(self.conn, dataset_id)
