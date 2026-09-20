import duckdb

conn = duckdb.connect('data/aquasynex.db')

indexes = [
    ("idx_ml_results_analysis", "ml_results(analysis_id)"),
    ("idx_ml_results_entity", "ml_results(entity_id, dataset_id)"),
    ("idx_ml_results_risk", "ml_results(analysis_id, risk_score)"),
    ("idx_transactions_dataset", "transactions(dataset_id)"),
    ("idx_transactions_timestamp", "transactions(dataset_id, timestamp)"),
    ("idx_tx_inputs_address", "transaction_inputs(input_address)"),
    ("idx_tx_outputs_address", "transaction_outputs(output_address)"),
    ("idx_addresses_dataset", "addresses(dataset_id)"),
    ("idx_analysis_dataset", "analysis_runs(dataset_id)"),
    ("idx_network_events_dataset", "network_events(dataset_id)"),
    ("idx_network_events_tx", "network_events(transaction_id)")
]

for idx_name, cols in indexes:
    try:
        conn.execute(f"DROP INDEX IF EXISTS {idx_name}")
        conn.execute(f"CREATE INDEX {idx_name} ON {cols}")
        print(f"Rebuilt {idx_name} on {cols}")
    except Exception as e:
        print(f"Error rebuilding {idx_name}: {e}")

conn.close()
