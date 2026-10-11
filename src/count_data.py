import sqlite3

conn = sqlite3.connect('npra.db')

# total
total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
print(f'数据库总数: {total}')

# 按 DCA 统计
print('\n按 DCA 统计:')
for row in conn.execute('SELECT dca, COUNT(*) FROM products GROUP BY dca ORDER BY dca'):
    print(f'  {row[0]}: {row[1]}')

conn.close()