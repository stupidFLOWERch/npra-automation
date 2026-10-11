import sqlite3

conn = sqlite3.connect('npra.db')

# total records
total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
print(f'Total records: {total}')

# per-DCA breakdown
print('\nRecords per DCA:')
for row in conn.execute('SELECT dca, COUNT(*) FROM products GROUP BY dca ORDER BY dca'):
    print(f'  {row[0]}: {row[1]}')

conn.close()