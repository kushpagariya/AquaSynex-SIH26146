# Deployment Checklist

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## Pre-Deployment Checklist

### Code Quality
- [ ] All unit tests pass
- [ ] All API tests pass
- [ ] All contract tests pass
- [ ] No `TODO` or `FIXME` in critical paths
- [ ] No debug logging statements left in production paths

### ML
- [ ] Trained model artifact present in `models/{model_id}/{version}/`
- [ ] `model_metadata.json` exists for each model
- [ ] Model loads successfully in backend container
- [ ] `/api/models` returns at least one model
- [ ] `/api/health` shows `modelsAvailable` non-empty

### Backend
- [ ] `GET /api/health` returns `200` with `status: "healthy"`
- [ ] DuckDB tables are created on startup (migrations run)
- [ ] Dataset upload works (`POST /api/datasets/upload`)
- [ ] Analysis triggers and completes (`POST /api/datasets/{id}/analyses`)

### Frontend
- [ ] Production build succeeds (`npm run build`)
- [ ] All pages load without console errors
- [ ] Graph visualization renders correctly
- [ ] Risk badges display correct colors
- [ ] BTC values display with 8 decimal places

### Offline Verification
- [ ] Disconnect internet; verify all features still work
- [ ] No network requests to external URLs in browser DevTools Network tab
- [ ] Backend logs show no external connection attempts

### Docker
- [ ] `docker-compose up --build` succeeds from clean state
- [ ] `docker-compose ps` shows all services `Up (healthy)`
- [ ] Application accessible at `http://localhost:3000`

### Demo Dataset
- [ ] Demo dataset file is available
- [ ] Dataset uploads successfully
- [ ] Analysis completes within acceptable time
- [ ] Graph and risk results display correctly

---

*Last updated: 2026-09-11 | Owner: All*
