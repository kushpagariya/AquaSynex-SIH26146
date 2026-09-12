"""Transaction schemas matching docs/backend/request-response-schemas.md."""

from datetime import datetime
from typing import List, Optional
from backend.schemas.common import CamelModel
from backend.schemas.ml_results import MLResultSummary


class TransactionSummary(CamelModel):
    transaction_id: str
    block_height: Optional[int] = None
    timestamp: Optional[datetime] = None
    input_count: Optional[int] = None
    output_count: Optional[int] = None
    total_input_value_btc: Optional[str] = None  # 8-decimal string
    total_output_value_btc: Optional[str] = None  # 8-decimal string
    fee_btc: Optional[str] = None  # 8-decimal string
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None


class TransactionInputDetail(CamelModel):
    input_index: int
    input_address: Optional[str] = None
    input_value_btc: Optional[str] = None  # 8-decimal string


class TransactionOutputDetail(CamelModel):
    output_index: int
    output_address: Optional[str] = None
    output_value_btc: Optional[str] = None  # 8-decimal string
    script_type: Optional[str] = None


class TransactionDetail(TransactionSummary):
    block_hash: Optional[str] = None
    transaction_size_bytes: Optional[int] = None
    label: Optional[str] = None
    inputs: List[TransactionInputDetail] = []
    outputs: List[TransactionOutputDetail] = []
    ml_result: Optional[MLResultSummary] = None
