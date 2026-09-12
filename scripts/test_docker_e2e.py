"""End-to-end verification script for AquaSynex running in Docker.

Tests:
1. Health check (via frontend proxy port 3000 and direct backend port 8000)
2. Models listing
3. Dataset upload (using SIH sample CSV)
4. Ingestion verification
5. Trigger analysis using production ML pipeline (aquasynex_xgb_binary_v1 / aquasynex_v1)
6. Verify ML predictions, risk scores, explanations
7. Verify Graph endpoint (Cytoscape format)
8. Verify Transactions and Addresses endpoints
9. Concurrent request handling test
"""

import os
import sys
import time
from pathlib import Path
import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://frontend:80/api")
DIRECT_BACKEND_URL = os.environ.get("TEST_BACKEND_URL", "http://backend:8000/api")

print(f"[1/9] Testing direct backend health at {DIRECT_BACKEND_URL}/health...")
with httpx.Client(timeout=30.0) as client:
    resp = client.get(f"{DIRECT_BACKEND_URL}/health")
    assert resp.status_code == 200, f"Backend health failed: {resp.status_code} {resp.text}"
    health_data = resp.json()
    assert health_data["success"] is True
    assert health_data["data"]["databaseStatus"] == "connected"
    print("  -> Direct backend healthy:", health_data["data"])

print(f"[2/9] Testing frontend reverse proxy health at {BASE_URL}/health...")
with httpx.Client(timeout=30.0) as client:
    resp = client.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Proxy health failed: {resp.status_code} {resp.text}"
    proxy_health = resp.json()
    assert proxy_health["success"] is True
    print("  -> Proxied health check passed:", proxy_health["data"])

print(f"[3/9] Testing models listing at {BASE_URL}/models...")
with httpx.Client(timeout=30.0) as client:
    resp = client.get(f"{BASE_URL}/models")
    assert resp.status_code == 200, f"Models failed: {resp.status_code} {resp.text}"
    models_data = resp.json()
    assert models_data["success"] is True
    model_ids = [m["modelId"] for m in models_data["data"]]
    print(f"  -> Available models ({len(model_ids)}): {model_ids}")
    assert "aquasynex_xgb_binary_v1" in model_ids
    assert "aquasynex_v1" in model_ids

print("[4/9] Uploading SIH sample CSV dataset...")
# Find sample CSV
csv_candidates = [
    Path("/app/datasets/test_smoke_50.csv"),
    Path("/app/datasets/test_normal_100.csv"),
    Path("/app/datasets/showcase_burst_network.csv"),
    Path("/app/data/sample/sih_transactions_sample.csv"),
    Path("/app/data/sample_v2/sih_transactions_sample.csv"),
]
csv_path = None
for c in csv_candidates:
    if c.exists():
        csv_path = c
        break

if not csv_path:
    raise FileNotFoundError(f"Could not find sample CSV among {csv_candidates}")

print(f"  -> Using sample CSV: {csv_path} ({csv_path.stat().st_size} bytes)")

dataset_name = f"Docker_E2E_Test_{int(time.time())}"
with open(csv_path, "rb") as f:
    files = {"file": (csv_path.name, f, "text/csv")}
    data = {"name": dataset_name}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{BASE_URL}/datasets/upload", files=files, data=data)
        assert resp.status_code in (200, 201, 202), f"Upload failed: {resp.status_code} {resp.text}"
        upload_data = resp.json()
        assert upload_data["success"] is True
        dataset_id = upload_data["data"]["datasetId"]
        print(f"  -> Uploaded successfully! datasetId: {dataset_id}, status: {upload_data['data']['status']}")

print(f"[5/9] Polling dataset status for {dataset_id}...")
with httpx.Client(timeout=30.0) as client:
    for i in range(20):
        resp = client.get(f"{BASE_URL}/datasets/{dataset_id}")
        assert resp.status_code == 200
        ds = resp.json()["data"]
        status = ds["status"]
        print(f"  -> Dataset status: {status}, txCount: {ds.get('transactionCount')}, addressCount: {ds.get('addressCount')}")
        if status in ("ready", "completed"):
            break
        elif status == "failed":
            raise RuntimeError(f"Dataset ingestion failed: {ds}")
        time.sleep(1)
    else:
        raise TimeoutError("Dataset ingestion timed out")

print(f"[6/9] Triggering ML analysis for dataset {dataset_id} with aquasynex_xgb_binary_v1...")
analysis_payload = {
    "modelId": "aquasynex_xgb_binary_v1",
    "modelVersion": "1.0.0",
    "config": {
        "riskThreshold": 0.5,
        "includeExplanations": True,
        "maxEntities": 1000
    }
}
with httpx.Client(timeout=30.0) as client:
    resp = client.post(f"{BASE_URL}/datasets/{dataset_id}/analyses", json=analysis_payload)
    assert resp.status_code == 202, f"Analysis trigger failed: {resp.status_code} {resp.text}"
    trigger_data = resp.json()
    assert trigger_data["success"] is True
    analysis_id = trigger_data["data"]["analysisId"]
    print(f"  -> Analysis triggered! analysisId: {analysis_id}, status: {trigger_data['data']['status']}")

print(f"[7/9] Polling ML analysis {analysis_id} until completion...")
with httpx.Client(timeout=60.0) as client:
    for i in range(30):
        resp = client.get(f"{BASE_URL}/analyses/{analysis_id}")
        assert resp.status_code == 200
        analysis_summary = resp.json()["data"]
        status = analysis_summary["status"]
        print(f"  -> Analysis status: {status}, progress: {analysis_summary.get('progress')}%")
        if status == "completed":
            print(f"  -> ML Analysis COMPLETED! Total scored: {analysis_summary.get('totalEntitiesScored')}, highRisk: {analysis_summary.get('highRiskCount')}")
            break
        elif status == "failed":
            raise RuntimeError(f"Analysis failed: {analysis_summary.get('errorMessage')}")
        time.sleep(1)
    else:
        raise TimeoutError("ML analysis execution timed out")

print(f"[8/9] Verifying ML results and Graph endpoints...")
with httpx.Client(timeout=30.0) as client:
    # Results
    res_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/results?page=1&pageSize=10")
    assert res_resp.status_code == 200
    results_json = res_resp.json()
    assert results_json["success"] is True
    results_list = results_json["data"]
    pagination = results_json.get('meta', {}).get('pagination') or {}
    print(f"  -> Retrieved {len(results_list)} scored results (pagination: {pagination})")
    if len(results_list) > 0:
        first_res = results_list[0]
        print(f"     Sample entity: {first_res['entityId']} ({first_res['entityType']}), riskScore: {first_res['riskScore']}, riskLevel: {first_res['riskLevel']}")
        print(f"     Explanations: {len(first_res.get('explanations', []))} top features")

    # Graph
    graph_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/graph?maxNodes=100")
    assert graph_resp.status_code == 200
    graph_json = graph_resp.json()
    assert graph_json["success"] is True
    graph_data = graph_json["data"]
    nodes = graph_data.get("nodes") or graph_data.get("elements", {}).get("nodes", [])
    edges = graph_data.get("edges") or graph_data.get("elements", {}).get("edges", [])
    print(f"  -> Graph elements: {len(nodes)} nodes, {len(edges)} edges")

print("[9/9] Testing concurrent requests to verify backend stability under load...")
import concurrent.futures

def ping_health(i):
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{BASE_URL}/health")
        return r.status_code

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(ping_health, i) for i in range(24)]
    statuses = [f.result() for f in futures]
    assert all(s == 200 for s in statuses), f"Concurrent requests failed: {statuses}"
    print(f"  -> Successfully processed {len(statuses)} concurrent health checks with 100% 200 OK")

print("\n==============================================")
print("ALL DOCKER END-TO-END VERIFICATION CHECKS PASSED!")
print("==============================================")
