import duckdb
from backend.services.graph_service import GraphService

conn = duckdb.connect('data/aquasynex.db')
gs = GraphService(conn)

runs = conn.execute("SELECT analysis_id, dataset_id FROM analysis_runs WHERE status = 'completed'").fetchall()
for a_id, ds_id in runs:
    try:
        g = gs.get_analysis_graph(a_id)
        edge_count = len(g['edges'])
        node_count = len(g['nodes'])
        ml_count = conn.execute("SELECT count(*) FROM ml_results WHERE analysis_id = ?", [a_id]).fetchone()[0]
        alert_count = conn.execute("SELECT count(*) FROM alerts WHERE analysis_id = ?", [a_id]).fetchone()[0]
        print(f"Analysis {a_id[:8]} (ds {ds_id[:8]}): nodes={node_count}, edges={edge_count}, ml={ml_count}, alerts={alert_count}")
    except Exception as e:
        print(f"Analysis {a_id[:8]} error: {e}")

conn.close()
