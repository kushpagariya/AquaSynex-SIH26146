import duckdb

conn = duckdb.connect('data/aquasynex.db')
print("Datasets row counts across tables:")
datasets = conn.execute("SELECT dataset_id, name FROM datasets").fetchall()
for ds_id, name in datasets:
    tx_cnt = conn.execute("SELECT count(*) FROM transactions WHERE dataset_id = ?", [ds_id]).fetchone()[0]
    in_cnt = conn.execute("SELECT count(*) FROM transaction_inputs WHERE dataset_id = ?", [ds_id]).fetchone()[0]
    out_cnt = conn.execute("SELECT count(*) FROM transaction_outputs WHERE dataset_id = ?", [ds_id]).fetchone()[0]
    addr_cnt = conn.execute("SELECT count(*) FROM addresses WHERE dataset_id = ?", [ds_id]).fetchone()[0]
    ml_cnt = conn.execute("SELECT count(*) FROM ml_results WHERE dataset_id = ?", [ds_id]).fetchone()[0]
    alert_cnt = conn.execute("SELECT count(*) FROM alerts WHERE dataset_id = ?", [ds_id]).fetchone()[0]
    print(f"Dataset {ds_id[:8]} ({name}) | tx: {tx_cnt} | in: {in_cnt} | out: {out_cnt} | addr: {addr_cnt} | ml: {ml_cnt} | alerts: {alert_cnt}")

conn.close()
