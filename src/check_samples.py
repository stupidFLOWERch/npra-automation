import sqlite3

conn = sqlite3.connect('npra.db')

print('=== Random sample across all DCAs ===\n')
for row in conn.execute("""
    SELECT dca, registration_no, product_name, holder, manufacturer,
           status, category, register_date, expiry_date
    FROM products
    ORDER BY RANDOM()
    LIMIT 10
"""):
    print(f'[{row[0]}]')
    print(f'  Registration No.: {row[1]}')
    print(f'  Product Name: {row[2]}')
    print(f'  Holder: {row[3]}')
    print(f'  Manufacturer: {row[4]}')
    print(f'  Status: {row[5]}')
    print(f'  Category: {row[6]}')
    print(f'  Register Date: {row[7]}')
    print(f'  Expiry Date: {row[8]}')
    print()

conn.close()