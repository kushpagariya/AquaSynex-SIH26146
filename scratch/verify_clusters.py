import duckdb
from collections import Counter

conn = duckdb.connect('data/aquasynex.db', read_only=True)

test_datasets = [
    ('showcase_coordinated_multihop', 'd194641d-e9ed-4a4b-96ce-448063bf6517'),
    ('test_normal_100', '29ced22b-6104-4b4b-8fde-94fa904c4bab')
]

for label, ds_id in test_datasets:
    print(f"\n=================== Dataset: {label} ({ds_id}) ===================")
    
    # Latest completed analysis
    run = conn.execute(
        "SELECT analysis_id, model_id FROM analysis_runs WHERE dataset_id = ? AND status = 'completed' ORDER BY started_at DESC LIMIT 1",
        [ds_id]
    ).fetchone()
    if not run:
        print("No completed analysis run.")
        continue
    analysis_id, model_id = run
    print(f"Analysis: {analysis_id} ({model_id})")
    
    # ML results
    ml_rows = conn.execute(
        "SELECT entity_id, risk_score, risk_level, prediction_label FROM ml_results WHERE analysis_id = ? AND entity_type = 'transaction'",
        [analysis_id]
    ).fetchall()
    results_map = {r[0]: {'risk_score': round(r[1] * 100), 'risk_level': r[2], 'prediction_label': r[3]} for r in ml_rows}
    print(f"Total transaction ML results indexed: {len(results_map)}")
    
    # Alerts
    alert_rows = conn.execute(
        "SELECT alert_id, transaction_id, entity_id, alert_type, severity, priority, status FROM alerts WHERE dataset_id = ?",
        [ds_id]
    ).fetchall()
    print(f"Total persistent alerts in DB for dataset: {len(alert_rows)}")
    
    # Inputs & outputs to map addresses to transactions
    in_rows = conn.execute(
        "SELECT transaction_id, input_address FROM transaction_inputs WHERE dataset_id = ? AND input_address IS NOT NULL",
        [ds_id]
    ).fetchall()
    out_rows = conn.execute(
        "SELECT transaction_id, output_address FROM transaction_outputs WHERE dataset_id = ? AND output_address IS NOT NULL",
        [ds_id]
    ).fetchall()
    
    addr_to_tx = {}
    tx_to_addr = {}
    for txid, addr in in_rows + out_rows:
        if addr not in addr_to_tx:
            addr_to_tx[addr] = set()
        addr_to_tx[addr].add(txid)
        if txid not in tx_to_addr:
            tx_to_addr[txid] = set()
        tx_to_addr[txid].add(addr)
            
    # Bipartite component clustering
    visited_addrs = set()
    clusters = []
    
    for start_addr in addr_to_tx:
        if start_addr in visited_addrs:
            continue
        comp_addrs = set([start_addr])
        comp_txs = set()
        queue = [start_addr]
        visited_addrs.add(start_addr)
        
        while queue:
            curr_addr = queue.pop(0)
            txs = addr_to_tx.get(curr_addr, set())
            for tx in txs:
                if tx not in comp_txs:
                    comp_txs.add(tx)
                    for neighbor_addr in tx_to_addr.get(tx, set()):
                        if neighbor_addr not in visited_addrs:
                            visited_addrs.add(neighbor_addr)
                            comp_addrs.add(neighbor_addr)
                            queue.append(neighbor_addr)
                            
        risks = [results_map[tx]['risk_score'] for tx in comp_txs if tx in results_map]
        behaviors = [results_map[tx]['prediction_label'] for tx in comp_txs if tx in results_map and results_map[tx]['prediction_label']]
        
        highest_risk = max(risks) if risks else 0
        dom_behavior = Counter(behaviors).most_common(1)[0][0] if behaviors else 'normal'
        
        c_alerts = [al for al in alert_rows if al[1] in comp_txs or al[2] in comp_txs or al[2] in comp_addrs]
        active_alerts = [al for al in c_alerts if str(al[6]).upper() not in ('RESOLVED', 'DISMISSED')]
        
        clusters.append({
            'size': len(comp_addrs),
            'tx_count': len(comp_txs),
            'highest_risk': highest_risk,
            'dominant_behavior': dom_behavior,
            'active_alerts': len(active_alerts),
            'total_alerts': len(c_alerts),
            'lead_address': sorted(list(comp_addrs))[0],
            'sample_alert': active_alerts[0] if active_alerts else None
        })
        
    clusters.sort(key=lambda x: (x['highest_risk'], x['active_alerts']), reverse=True)
    print(f"Total Inferred Clusters Formed: {len(clusters)}")
    for i, c in enumerate(clusters[:4]):
        print(f"  Cluster IBC-{i+1:02d}:")
        print(f"    Addresses: {c['size']}, Transactions: {c['tx_count']}")
        print(f"    Highest Risk: {c['highest_risk']} / 100")
        print(f"    Dominant Behavior: {c['dominant_behavior']}")
        print(f"    Active Alerts: {c['active_alerts']}, Total Alerts: {c['total_alerts']}")
        print(f"    Representative Address: {c['lead_address']}")
        if c['sample_alert']:
            print(f"    Sample Alert ID: {c['sample_alert'][0]}, Type: {c['sample_alert'][3]}, Severity: {c['sample_alert'][4]}, Priority: {c['sample_alert'][5]}")

conn.close()
