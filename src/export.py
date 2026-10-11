import sqlite3
import csv
import os

os.makedirs('samples', exist_ok=True)

conn = sqlite3.connect('npra.db')

with open('samples/sample-export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['dca', 'registration_no', 'product_name', 'holder',
                     'manufacturer', 'status', 'category', 'register_date', 'expiry_date'])

    # get first 3 data for each DCA
    dcas = [row[0] for row in conn.execute("SELECT DISTINCT dca FROM products ORDER BY dca")]
    for dca in dcas:
        for row in conn.execute("""
            SELECT dca, registration_no, product_name, holder, manufacturer,
                   status, category, register_date, expiry_date
            FROM products
            WHERE dca = ?
            LIMIT 3
        """, (dca,)):
            writer.writerow(row)

print(f'Exported {len(dcas) * 3} rows (3 per DCA) to samples/sample-export.csv')
conn.close()