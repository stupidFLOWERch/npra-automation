import pdfplumber
import sqlite3
import os
import re

DB_PATH = 'npra.db'

# ---- 1. Create table ----
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

# ---- 2. Parse a single PDF ----
def parse_pdf(pdf_path, dca):
    records = []
    global_col_idx = None   # column index cache, resolved once from the first header
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # check whether row 0 of this page is a header
                col_idx = find_column_indexes(table[0])

                if col_idx is not None:
                    # this page has a header
                    global_col_idx = col_idx   # update the cached column index
                    data_start = 1             # skip the header row
                else:
                    # this page has no header (continuation page)
                    if global_col_idx is None:
                        continue                # no header found yet, skip
                    col_idx = global_col_idx
                    data_start = 0             # all rows are data

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
    """Resolve column index for each field from the header row."""
    # normalize header text (trim, collapse whitespace, lowercase)
    normalized = [clean(h).lower() if h else '' for h in header]

    def find(*keywords):
        """Return the index of the first column containing any keyword."""
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

    # if any key field is missing, treat the row as not a header
    if any(v is None for v in idx.values()):
        return None

    return idx

def clean(s):
    if s is None:
        return ''
    # join hyphenated line breaks without inserting a space
    s = re.sub(r'-\s*\n\s*', '-', s)
    # remaining newlines -> space
    s = s.replace('\n', ' ')
    # collapse multiple whitespace into a single space
    return re.sub(r'\s+', ' ', s).strip()

# ---- 3. Extract DCA code from filename ----
def dca_from_filename(filename):
    m = re.search(r'DCA(\d+)', filename, re.IGNORECASE)
    return f'DCA{m.group(1)}' if m else None

# ---- 4. Main ----
def main():
    conn = init_db()
    downloads = 'downloads'
    files = sorted(f for f in os.listdir(downloads) if f.endswith('.pdf'))
    print(f'Found {len(files)} PDFs')

    # detect which DCAs are not yet in the database
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

    # parse only the new files
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

    # summary
    total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    print(f'\nTotal records in DB: {total}')
    conn.close()

if __name__ == '__main__':
    main()