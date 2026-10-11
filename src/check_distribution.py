import sqlite3
from collections import Counter

conn = sqlite3.connect('npra.db')

print('=== 同一 DCA 里重复的 registration_no ===\n')

dupes = list(conn.execute("""
    SELECT dca, registration_no, COUNT(*) as c
    FROM products
    GROUP BY dca, registration_no
    HAVING c > 1
    ORDER BY dca, registration_no
"""))

if not dupes:
    print('  无重复')
else:
    print(f'共 {len(dupes)} 组重复\n')
    for dca, reg, count in dupes:
        print(f'[{dca}] {reg} × {count}')
        for row in conn.execute("""
            SELECT status, register_date, expiry_date, product_name
            FROM products
            WHERE dca = ? AND registration_no = ?
        """, (dca, reg)):
            print(f'    status={row[0]!r}')
            print(f'    register_date={row[1]}, expiry_date={row[2]}')
            print(f'    product_name={row[3][:60]}')
        print()

conn.close()