import duckdb

conn = duckdb.connect('data/aquasynex.db')
analysis_id = '2b2eafaa-dbdc-44ae-9a99-7057e6563e7f'

# Check alerts for this analysis or transactions
tx_alerts = conn.execute("""
    SELECT a.alert_id, a.alert_type, a.severity, a.priority, a.status, a.entity_id, a.transaction_id
    FROM alerts a
""").fetchall()

print(f"Total alerts in database: {len(tx_alerts)}")

# Check if alerts match analysis or dataset
ds_id = conn.execute("SELECT dataset_id FROM analysis_runs WHERE analysis_id = ?", [analysis_id]).fetchone()[0]
alerts_for_ds = conn.execute("SELECT alert_id, alert_type, severity, priority, status, entity_id, transaction_id FROM alerts WHERE dataset_id = ?", [ds_id]).fetchall()
print(f"Alerts directly for dataset {ds_id}: {len(alerts_for_ds)}")

# Check if any alert transaction_id matches transactions of dataset 0b52b79d
matched_alerts = conn.execute("""
    SELECT a.alert_id, a.alert_type, a.severity, a.priority, a.status, a.entity_id, a.transaction_id
    FROM alerts a
    JOIN transactions t ON a.dataset_id = t.dataset_id AND (a.transaction_id = t.transaction_id OR a.entity_id = t.transaction_id)
    WHERE t.dataset_id = ?
""", [ds_id]).fetchall()
print(f"Alerts matching transactions in dataset: {len(matched_alerts)}")

# Check across ALL datasets which ones have alerts matching transactions
match_summary = conn.execute("""
    SELECT t.dataset_id, count(distinct a.alert_id)
    FROM alerts a
    JOIN transactions t ON a.dataset_id = t.dataset_id AND (a.transaction_id = t.transaction_id OR a.entity_id = t.transaction_id)
    GROUP BY t.dataset_id
""").fetchall()
print("Alert matches by dataset:")
for ds, c in match_summary:
    name = conn.execute("SELECT name FROM datasets WHERE dataset_id = ?", [ds]).fetchone()[0]
    print(f"Dataset {ds[:8]} ({name}): {c} alerts")

conn.close()
