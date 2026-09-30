import duckdb

conn = duckdb.connect('data/aquasynex.db')
target = '2b2eafaa-dbdc-44ae-9a99-7057e6563e7f'

print("Before reindexing:")
r1 = conn.execute("SELECT count(*) FROM ml_results WHERE analysis_id = ?", [target]).fetchone()
print("Direct index query:", r1)

conn.execute("DROP INDEX IF EXISTS idx_ml_results_analysis")
conn.execute("CREATE INDEX idx_ml_results_analysis ON ml_results(analysis_id)")

print("After reindexing:")
r2 = conn.execute("SELECT count(*) FROM ml_results WHERE analysis_id = ?", [target]).fetchone()
print("Direct index query after recreate:", r2)
conn.close()
