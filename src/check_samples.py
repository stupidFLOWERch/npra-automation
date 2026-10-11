import sqlite3

conn = sqlite3.connect('npra.db')

print('=== 随机抽查 10 条（跨所有 DCA）===\n')
for row in conn.execute("""
    SELECT dca, registration_no, product_name, holder, manufacturer,
           status, category, register_date, expiry_date
    FROM products
    ORDER BY RANDOM()
    LIMIT 10
"""):
    print(f'[{row[0]}]')
    print(f'  No. Pendaftaran MAL: {row[1]}')
    print(f'  Nama Produk: {row[2]}')
    print(f'  Pemegang: {row[3]}')
    print(f'  Pengilang: {row[4]}')
    print(f'  Status: {row[5]}')
    print(f'  Kategori: {row[6]}')
    print(f'  Tarikh Daftar: {row[7]}')
    print(f'  Tarikh Luput: {row[8]}')
    print()

conn.close()