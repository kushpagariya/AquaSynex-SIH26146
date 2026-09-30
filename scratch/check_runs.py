import duckdb

conn = duckdb.connect('data/aquasynex.db')
print("All analysis_runs:")
runs = conn.execute("SELECT analysis_id, dataset_id, status, entity_count, high_risk_count, critical_risk_count FROM analysis_runs").fetchall()
for r in runs:
    cnt = conn.execute("SELECT count(*) FROM ml_results WHERE analysis_id = ?", [r[0]]).fetchone()[0]
    print(f"Run: {r[0]} | Dataset: {r[1]} | Status: {r[2]} | entity_count: {r[3]} | actual ml_results: {cnt}")

conn.close()
