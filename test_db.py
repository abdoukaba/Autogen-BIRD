import sqlite3
conn = sqlite3.connect("california_schools.sqlite")
cursor = conn.cursor()

# List all tables
print("Tables in DB:", cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall())

# Show schema for 'schools'
print("Schema for schools:")
print(cursor.execute("PRAGMA table_info('schools');").fetchall())
conn.close()
