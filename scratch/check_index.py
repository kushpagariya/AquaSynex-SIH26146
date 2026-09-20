import duckdb

conn = duckdb.connect('data/aquasynex.db')
target = '2b2eafaa-dbdc-44ae-9a99-7057e6563e7f'
r1 = conn.execute("SELECT count(*) FROM ml_results WHERE analysis_id = ?", [target]).fetchone()
print("Direct index query:", r1)
r2 = conn.execute("SELECT count(*) FROM ml_results WHERE concat(analysis_id, '') = ?", [target]).fetchone()
print("Expression query (no index):", r2)
conn.close()
