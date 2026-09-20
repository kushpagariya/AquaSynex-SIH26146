import duckdb
from backend.services.graph_service import GraphService
from backend.services.result_service import ResultService
from collections import Counter

conn = duckdb.connect('data/aquasynex.db')
analysis_id = '2b2eafaa-dbdc-44ae-9a99-7057e6563e7f'

# Fetch dataset_id
ds_id = conn.execute("SELECT dataset_id FROM analysis_runs WHERE analysis_id = ?", [analysis_id]).fetchone()[0]

gs = GraphService(conn)
g = gs.get_analysis_graph(analysis_id)

rs = ResultService(conn)
results, _ = rs.list_results(analysis_id, page=1, page_size=500)
res_map = {r['entity_id']: r for r in results}

# Fetch persistent alerts
alerts_rows = conn.execute("""
    SELECT alert_id, alert_type, severity, priority, status, entity_id, transaction_id
    FROM alerts
""").fetchall()

alerts_by_tx = {}
alerts_by_entity = {}
for a in alerts_rows:
    aid, atype, asev, aprio, astatus, aeid, atxid = a
    alert_obj = {
        'alertId': aid,
        'alertType': atype,
        'severity': asev,
        'priority': aprio,
        'status': astatus,
        'entityId': aeid,
        'transactionId': atxid,
    }
    if atxid:
        alerts_by_tx.setdefault(atxid, []).append(alert_obj)
    if aeid:
        alerts_by_entity.setdefault(aeid, []).append(alert_obj)

# Map edge txs
addr_to_txs = {}
for e in g['edges']:
    src = e['source']
    tgt = e['target']
    for tx in e.get('transactions', []):
        txid = tx['transactionId']
        addr_to_txs.setdefault(src, set()).add(txid)
        addr_to_txs.setdefault(tgt, set()).add(txid)

adj = {n['id']: set() for n in g['nodes']}
for e in g['edges']:
    adj.setdefault(e['source'], set()).add(e['target'])
    adj.setdefault(e['target'], set()).add(e['source'])

visited = set()
clusters = []
cluster_idx = 1

for n in g['nodes']:
    nid = n['id']
    if nid in visited:
        continue
    comp = []
    q = [nid]
    visited.add(nid)
    while q:
        curr = q.pop(0)
        comp.append(curr)
        for nbr in adj.get(curr, set()):
            if nbr not in visited:
                visited.add(nbr)
                q.append(nbr)
    
    comp_set = set(comp)
    cluster_txs = set()
    for addr in comp:
        cluster_txs.update(addr_to_txs.get(addr, set()))
    
    risks = []
    behaviors = []
    for txid in cluster_txs:
        r = res_map.get(txid)
        if r:
            risks.append(round(r['risk_score'] * 100))
            if r.get('prediction_label'):
                behaviors.append(r['prediction_label'])
    
    highest_risk = max(risks) if risks else 0
    avg_risk = round(sum(risks) / len(risks)) if risks else 0
    b_counts = Counter(behaviors)
    dominant_behavior = b_counts.most_common(1)[0][0] if b_counts else 'normal'

    # Collect cluster alerts
    c_alerts = []
    seen_alert_ids = set()
    for txid in cluster_txs:
        for al in alerts_by_tx.get(txid, []) + alerts_by_entity.get(txid, []):
            if al['alertId'] not in seen_alert_ids:
                seen_alert_ids.add(al['alertId'])
                c_alerts.append(al)
    for addr in comp:
        for al in alerts_by_entity.get(addr, []):
            if al['alertId'] not in seen_alert_ids:
                seen_alert_ids.add(al['alertId'])
                c_alerts.append(al)

    active_alerts = [a for a in c_alerts if a['status'] not in ('RESOLVED', 'DISMISSED')]

    clusters.append({
        'clusterId': f"IBC-{cluster_idx:02d}",
        'clusterSize': len(comp),
        'transactionCount': len(cluster_txs),
        'highestRisk': highest_risk,
        'averageRisk': avg_risk,
        'dominantBehavior': dominant_behavior,
        'totalAlerts': len(c_alerts),
        'activeAlerts': len(active_alerts),
        'alertsSample': active_alerts[:2],
    })
    cluster_idx += 1

print(f"Total clusters: {len(clusters)}")
with_alerts = [c for c in clusters if c['activeAlerts'] > 0]
print(f"Clusters with active alerts: {len(with_alerts)} / {len(clusters)}")
print("Sample clusters with active alerts:")
for c in with_alerts[:5]:
    print(c)

print("\nSample clusters without alerts:")
without_alerts = [c for c in clusters if c['activeAlerts'] == 0]
for c in without_alerts[:3]:
    print(c)

conn.close()
