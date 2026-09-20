import duckdb
from backend.services.graph_service import GraphService
from backend.services.result_service import ResultService
from collections import Counter

conn = duckdb.connect('data/aquasynex.db')
analysis_id = '2b2eafaa-dbdc-44ae-9a99-7057e6563e7f'

count = conn.execute("SELECT count(*) FROM ml_results WHERE analysis_id = ?", [analysis_id]).fetchone()[0]
print(f"ML results for analysis {analysis_id}: {count}")

gs = GraphService(conn)
g = gs.get_analysis_graph(analysis_id)
print(f"Graph nodes: {len(g['nodes'])}, edges: {len(g['edges'])}")

rs = ResultService(conn)
results, _ = rs.list_results(analysis_id, page=1, page_size=500)
print(f"ResultService returned {len(results)} items")
res_map = {(r.get('entityId') or r.get('entity_id')): r for r in results}

# Check edge transactions matching res_map
edge_txs = set()
for e in g['edges']:
    for tx in e.get('transactions', []):
        edge_txs.add(tx['transactionId'])

matched = edge_txs.intersection(set(res_map.keys()))
print(f"Total unique edge txs: {len(edge_txs)}, matched with ml_results: {len(matched)}")

# Group connected components of addresses
adj = {n['id']: set() for n in g['nodes']}
for e in g['edges']:
    adj.setdefault(e['source'], set()).add(e['target'])
    adj.setdefault(e['target'], set()).add(e['source'])

visited = set()
clusters = []
cluster_idx = 1

# Map edge txs by address for direct lookup
addr_to_txs = {}
for e in g['edges']:
    src = e['source']
    tgt = e['target']
    for tx in e.get('transactions', []):
        txid = tx['transactionId']
        addr_to_txs.setdefault(src, set()).add(txid)
        addr_to_txs.setdefault(tgt, set()).add(txid)

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
    # Collect all member transactions for this cluster
    cluster_txs = set()
    for addr in comp:
        cluster_txs.update(addr_to_txs.get(addr, set()))
    
    # Collect member risk scores & behaviors from persisted ml_results
    risks = []
    behaviors = []
    for txid in cluster_txs:
        r = res_map.get(txid)
        if r:
            score = r.get('riskScore') if r.get('riskScore') is not None else r.get('risk_score', 0)
            risks.append(round(score * 100))
            label = r.get('predictionLabel') or r.get('prediction_label')
            if label:
                behaviors.append(label)
    
    highest_risk = max(risks) if risks else 0
    avg_risk = round(sum(risks) / len(risks)) if risks else 0
    b_counts = Counter(behaviors)
    dominant_behavior = b_counts.most_common(1)[0][0] if b_counts else 'normal'

    clusters.append({
        'clusterId': f"IBC-{str(cluster_idx).padStart(2, '0')}" if hasattr(str, 'padStart') else f"IBC-{cluster_idx:02d}",
        'clusterSize': len(comp),
        'transactionCount': len(cluster_txs),
        'highestRisk': highest_risk,
        'averageRisk': avg_risk,
        'dominantBehavior': dominant_behavior,
        'riskCount': len(risks),
    })
    cluster_idx += 1

print(f"Total clusters formed: {len(clusters)}")
non_zero = [c for c in clusters if c['highestRisk'] > 0]
print(f"Clusters with non-zero risk: {len(non_zero)} / {len(clusters)}")
print("Top 10 clusters by highestRisk:")
for c in sorted(clusters, key=lambda x: x['highestRisk'], reverse=True)[:10]:
    print(c)

conn.close()
