# Request/Response Schemas

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> Pydantic schema definitions for all API requests and responses.
> See [api-specification.md](./api-specification.md) for endpoint-level documentation.

---

## 1. Common Schemas

### ApiMeta

```python
class ApiMeta(BaseModel):
    timestamp: datetime      # UTC ISO 8601
    requestId: str           # UUID v4

class PaginationMeta(BaseModel):
    page: int
    pageSize: int
    totalItems: int
    totalPages: int
    hasNext: bool
    hasPrev: bool
```

### ApiResponse (Generic)

```python
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ApiMeta

class ApiError(BaseModel):
    code: str
    message: str
    details: dict | None = None
```

---

## 2. Dataset Schemas

### DatasetSummary (in list)

```python
class DatasetSummary(BaseModel):
    datasetId: str
    name: str
    fileName: str
    format: str              # 'csv' | 'json' | 'jsonl' | 'parquet'
    sizeBytes: int
    rowCount: int | None
    status: str              # 'uploaded' | 'processing' | 'ready' | 'error'
    uploadedAt: datetime
    availableFields: list[str]
```

### DatasetDetail (full)

```python
class DatasetDetail(DatasetSummary):
    canonicalTxCount: int | None
    validationSummary: dict | None
    errorMessage: str | None
```

---

## 3. Analysis Schemas

### AnalysisRequest

```python
class AnalysisRequest(BaseModel):
    modelId: str | None = None
    modelVersion: str | None = None
    config: dict | None = None
```

### AnalysisSummary

```python
class AnalysisSummary(BaseModel):
    analysisId: str
    datasetId: str
    status: str              # 'pending' | 'running' | 'completed' | 'failed'
    startedAt: datetime | None
    completedAt: datetime | None
    modelId: str | None
    modelVersion: str | None
    entityCount: int | None
    highRiskCount: int | None
    criticalRiskCount: int | None
    errorMessage: str | None
```

---

## 4. Transaction Schemas

### TransactionSummary (in list)

```python
class TransactionSummary(BaseModel):
    transactionId: str
    blockHeight: int | None
    timestamp: datetime | None
    inputCount: int | None
    outputCount: int | None
    totalInputValueBtc: str | None      # 8-decimal string
    totalOutputValueBtc: str | None     # 8-decimal string
    feeBtc: str | None                  # 8-decimal string
    riskScore: float | None             # null if not analyzed
    riskLevel: str | None               # null if not analyzed
```

### TransactionDetail (full)

```python
class TransactionDetail(TransactionSummary):
    blockHash: str | None
    transactionSizeBytes: int | None
    label: str | None
    inputs: list[TransactionInputDetail]
    outputs: list[TransactionOutputDetail]
    mlResult: MLResultSummary | None

class TransactionInputDetail(BaseModel):
    inputIndex: int
    inputAddress: str | None
    inputValueBtc: str | None           # 8-decimal string

class TransactionOutputDetail(BaseModel):
    outputIndex: int
    outputAddress: str | None
    outputValueBtc: str | None          # 8-decimal string
    scriptType: str | None
```

---

## 5. Address Schemas

### AddressSummary (in list)

```python
class AddressSummary(BaseModel):
    addressId: str                      # Bitcoin address string
    transactionCount: int | None
    totalReceivedBtc: str | None        # 8-decimal string
    totalSentBtc: str | None            # 8-decimal string
    firstSeen: datetime | None
    lastSeen: datetime | None
    riskScore: float | None
    riskLevel: str | None
```

### AddressDetail (full)

```python
class AddressDetail(AddressSummary):
    addressType: str | None
    activeDays: int | None
    mlResult: MLResultDetail | None
```

---

## 6. ML Result Schemas

### MLResultSummary (used in lists / transaction/address detail)

```python
class MLResultSummary(BaseModel):
    entityId: str
    entityType: str
    anomalyScore: float
    riskScore: float
    riskLevel: str
    predictionLabel: str | None
    modelId: str
    modelVersion: str
    predictedAt: datetime
```

### MLResultDetail (full — with explanations)

```python
class MLResultDetail(MLResultSummary):
    confidence: float | None
    explanations: list[FeatureExplanationSchema]
    features: list[FeatureValueSchema]
    graphEvidence: list[GraphEvidenceSchema]

class FeatureExplanationSchema(BaseModel):
    featureName: str
    displayLabel: str
    shapValue: float
    direction: str                      # 'increases_risk' | 'decreases_risk' | 'neutral'
    importanceRank: int
    normalizedImportance: float
    featureValue: float | int | str | None
    featureUnit: str | None

class FeatureValueSchema(BaseModel):
    featureName: str
    rawValue: float | int | None
    normalizedValue: float | None
    isImputed: bool
    imputationMethod: str | None

class GraphEvidenceSchema(BaseModel):
    evidenceType: str
    label: str
    featureName: str
    value: float | int
    description: str
```

---

## 7. Model Schema

```python
class ModelInfo(BaseModel):
    modelId: str
    modelVersion: str
    algorithm: str
    modelType: str               # 'anomaly_detection' | 'classification'
    featureSchemaVersion: str
    trainingCompletedAt: datetime | None
```

---

## 8. BTC Value Field Rule

**All BTC value fields in API responses are returned as string-encoded 8-decimal-place decimal numbers.**

| Field name pattern | Type in response | Example |
|---|---|---|
| `*Btc` | `str \| null` | `"5.00000000"` |
| `*Satoshi` | `int \| null` | `500000000` |

The API **never** returns raw float for BTC values.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner*
*References: [api-specification.md](./api-specification.md) | [model-output-contract.md](../ml/model-output-contract.md)*
