import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('surikatajs.db')
cursor = conn.cursor()

# Execute a query
cursor.execute("SELECT * FROM alerts")

# Fetch and print the results
rows = cursor.fetchall()
for row in rows:
    print(row)

# Close the connection
conn.close()
