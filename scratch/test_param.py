import duckdb

conn = duckdb.connect('data/aquasynex.db', read_only=True)
ds_id = 'd99d8332-7362-4714-8ce0-113c2fc9189c'
print("WHERE count:", conn.execute("SELECT COUNT(*) FROM alerts WHERE dataset_id = ?", [ds_id]).fetchall())
print("Dataset name:", conn.execute("SELECT name FROM datasets WHERE dataset_id = ?", [ds_id]).fetchall())
conn.close()
