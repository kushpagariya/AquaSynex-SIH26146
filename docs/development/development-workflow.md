# Development Workflow

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## 1. Branch Strategy

```
main  ← stable integration branch
├── ml            ← ML pipeline, training, inference
├── backend       ← FastAPI backend
├── frontend      ← React frontend
├── data_pipeline ← Data ingestion, normalization
├── graph_analysis ← Graph construction, features
└── feature/xyz   ← Short-lived feature branches (merge into subsystem branch)
```

**Rules**:
- `main` is always deployable.
- Never force-push to `main`.
- Subsystem owners work on their respective branches.
- Integration happens through PRs from subsystem branches → `main`.

---

## 2. Development Workflow

```
1. Read relevant documentation
   │
2. Understand the contract you are implementing
   │
3. Create/checkout your subsystem branch
   │
4. Implement
   │
5. Write/update tests
   │
6. Check contract compliance
   │
7. If contract changed: update documentation
   │
8. Open Pull Request
   │
9. PR review by affected owners
   │
10. Merge
```

---

## 3. PR Checklist

Before merging any PR, verify:

**Code quality**
- [ ] Code follows naming conventions (see [naming-conventions.md](./naming-conventions.md))
- [ ] No hardcoded secrets or paths
- [ ] No internet calls at runtime
- [ ] Python: `snake_case` for variables/functions, `PascalCase` for classes
- [ ] TypeScript/React: `camelCase` for variables/hooks, `PascalCase` for components

**Testing**
- [ ] Unit tests pass: `pytest tests/unit/ -v`
- [ ] API tests pass: `pytest tests/api/ -v`
- [ ] Contract tests pass: `pytest tests/contracts/ -v`
- [ ] Frontend tests pass: `npm test`
- [ ] No failing tests introduced

**Documentation — required if any of the following changed**
- [ ] API endpoint added/modified → update [api-specification.md](../backend/api-specification.md)
- [ ] DuckDB table added/modified → update [duckdb-schema.md](../backend/duckdb-schema.md)
- [ ] Feature added/modified → update [feature-specification.md](../ml/feature-specification.md)
- [ ] ML output field added/modified → update [model-output-contract.md](../ml/model-output-contract.md)
- [ ] Graph schema changed → update [graph-schema.md](../graph/graph-schema.md)
- [ ] Environment variable added → update [environment-variables.md](../deployment/environment-variables.md)
- [ ] Error code added → update [error-handling.md](../backend/error-handling.md)
- [ ] Naming convention changed → update [naming-conventions.md](./naming-conventions.md)

**Architecture**
- [ ] No new technologies introduced without an ADR
- [ ] No cross-subsystem boundary violations
- [ ] Docker compatibility maintained

---

## 4. Commit Message Convention

```
<type>: <short description>

[optional body]

[optional footer: references to issues or ADRs]
```

**Types**:
| Type | When |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only change |
| `refactor` | Code change without behavior change |
| `test` | Adding or fixing tests |
| `chore` | Build, config, dependencies |
| `contract` | Shared contract change (requires multi-owner review) |

---

## 5. Local Development Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # Vite dev server on port 3000
```

### ML Pipeline

```bash
cd pipeline
pip install -r requirements.txt
python -m pipeline.ml.model_trainer --dataset-id <uuid>
```

### Full Stack (Docker)

```bash
docker-compose up --build
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: All*
