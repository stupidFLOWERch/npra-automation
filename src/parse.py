import pdfplumber
import sqlite3
import os
import re

DB_PATH = 'npra.db'

# ---- 1. 建表 ----
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dca TEXT,
            registration_no TEXT,
            product_name TEXT,
            holder TEXT,
            manufacturer TEXT,
            status TEXT,
            category TEXT,
            register_date TEXT,
            expiry_date TEXT,
            UNIQUE(registration_no, dca, status)
        )
    ''')
    conn.commit()
    return conn

# ---- 2. 解析一个 PDF ----
def parse_pdf(pdf_path, dca):
    records = []
    global_col_idx = None   # 全局表头索引，只找一次
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # 每页都判断：第 0 行是不是表头
                col_idx = find_column_indexes(table[0])

                if col_idx is not None:
                    # 这页有表头
                    global_col_idx = col_idx   # 更新全局索引
                    data_start = 1             # 跳过表头
                else:
                    # 这页没表头
                    if global_col_idx is None:
                        continue                # 还没找到表头，跳过
                    col_idx = global_col_idx
                    data_start = 0             # 从第 0 行开始（都是数据）

                for row in table[data_start:]:
                    if len(row) < max(col_idx.values()) + 1:
                        continue
                    if not row[col_idx['registration_no']] or not row[col_idx['product_name']]:
                        continue
                    records.append({
                        'dca': dca,
                        'registration_no': clean(row[col_idx['registration_no']]),
                        'product_name': clean(row[col_idx['product_name']]),
                        'holder': clean(row[col_idx['holder']]),
                        'manufacturer': clean(row[col_idx['manufacturer']]),
                        'status': clean(row[col_idx['status']]),
                        'category': clean(row[col_idx['category']]),
                        'register_date': clean(row[col_idx['register_date']]),
                        'expiry_date': clean(row[col_idx['expiry_date']]),
                    })

    return records


def find_column_indexes(header):
    """从表头找到每个字段的列索引"""
    # 规范化表头文字（去空格、换行、转小写）
    normalized = [clean(h).lower() if h else '' for h in header]

    def find(*keywords):
        """找第一个包含任一关键词的列"""
        for i, h in enumerate(normalized):
            for kw in keywords:
                if kw in h:
                    return i
        return None

    idx = {
        'registration_no': find('no. pendaftaran'),
        'product_name': find('nama produk'),
        'holder': find('pemegang'),
        'manufacturer': find('pengilang'),
        'status': find('status'),
        'category': find('kategori'),
        'register_date': find('tarikh daftar', 'tarikh\ndaftar'),
        'expiry_date': find('tarikh luput'),
    }

    # 如果关键字段找不到，返回 None
    if any(v is None for v in idx.values()):
        return None

    return idx

def clean(s):
    if s is None:
        return ''
    # 先处理「连字符 + 换行」：直接去掉换行，不加空格
    s = re.sub(r'-\s*\n\s*', '-', s)
    # 剩下的换行 → 空格
    s = s.replace('\n', ' ')
    # 多空白 → 单空格
    return re.sub(r'\s+', ' ', s).strip()
    
# ---- 3. 从文件名拿 DCA 编号 ----
def dca_from_filename(filename):
    m = re.search(r'DCA(\d+)', filename, re.IGNORECASE)
    return f'DCA{m.group(1)}' if m else None

# ---- 4. 主流程 ----
def main():
    conn = init_db()
    downloads = 'downloads'
    files = sorted(f for f in os.listdir(downloads) if f.endswith('.pdf'))
    print(f'Found {len(files)} PDFs')

    # 先检测：哪些 DCA 未入库
    new_files = []
    for filename in files:
        dca = dca_from_filename(filename)
        if not dca:
            print(f'[skip] {filename}: no DCA number')
            continue

        count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE dca = ?", (dca,)
        ).fetchone()[0]

        if count == 0:
            new_files.append((filename, dca))
        else:
            print(f'[skip] {dca}: already in DB ({count} records)')

    print(f'\nNew to parse: {len(new_files)}')

    if not new_files:
        print('No new documents. Nothing to parse.')
        conn.close()
        return

    # 只解析新的
    for filename, dca in new_files:
        path = os.path.join(downloads, filename)
        try:
            records = parse_pdf(path, dca)
            print(f'[{dca}] parsed {len(records)} records')

            for r in records:
                conn.execute('''
                    INSERT OR IGNORE INTO products
                    (dca, registration_no, product_name, holder, manufacturer,
                     status, category, register_date, expiry_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    r['dca'], r['registration_no'], r['product_name'],
                    r['holder'], r['manufacturer'], r['status'],
                    r['category'], r['register_date'], r['expiry_date']
                ))
            conn.commit()
        except Exception as e:
            print(f'[{dca}] FAILED: {e}')

    # 统计
    total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    print(f'\nTotal records in DB: {total}')
    conn.close()

if __name__ == '__main__':
    main()