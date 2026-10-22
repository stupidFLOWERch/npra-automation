# NPRA Automation

Playwright + Python pipeline that downloads approved product PDFs from NPRA and stores the extracted table data in SQLite. An n8n workflow supports scheduled monitoring and automated execution on Windows.

## What it does

1. **Historical Backfill** — Uses Playwright to navigate the NPRA page and download every PDF from DCA404 (Jan 2025) to the latest available month.
2. **Database Storage** — Parses each PDF's product table with `pdfplumber` and stores 8 fields per product (registration no., product name, holder, manufacturer, status, category, register date, expiry date) in SQLite.
3. **Recurring Monitor** — On re-runs, detects and processes only new documents. Already-downloaded PDFs and already-imported records are skipped.
4. **Scheduled Automation** — Uses n8n's Schedule Trigger to invoke a local Windows Runner, which executes the Playwright scraper and Python parser.

## Requirements
- Windows 10/11
- Node.js 18+
- Python 3.10+
- Docker Desktop
- n8n
- Chromium (installed through Playwright)

## Setup
### 1. Install Node deps
Open PowerShell in the project root:
```bash
npm install
```
### 2. Install Playwright browser
```bash
npx playwright install chromium
```
### 3. Create and Activate the Python Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\Activate
```

### 4. Install Python deps
```bash
pip install pdfplumber
```
## Usage

```bash
# Step 1: download PDFs (DCA404 to latest)
node src/scrape.js

# Step 2: parse PDFs and store into SQLite
python src/parse.py
```

Run the commands again later to check for newly published documents. Existing downloaded PDFs and previously imported DCA records are skipped.

## Local n8n Scheduled Automation

The workflow contains two nodes:

1. **Schedule Trigger** — Starts the automation at scheduled time.

2. **HTTP Request** — Sends a POST request to the local Windows Runner.

The Runner then executes the following pipeline:

```bash
n8n Schedule Trigger
        |
        v
n8n HTTP Request
        |
        v
Windows Runner (runner.js)
        |
        +--> Playwright: scrape NPRA and download PDFs
        |
        +--> Python: parse PDFs and update SQLite

```

### 1. Start n8n with Docker Desktop
If n8n has not been installed, start it with Docker:
```bash
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

If the n8n container already exists, start the existing container instead:

```bash
docker start n8n
```

Open n8n at:

http://localhost:5678

### 2. Import the Workflow

1. Create a workflow and import workflow/npra-workflow.json.

2. Open the HTTP Request node and verify its URL, Authorization header, and timeout.

3. Replace the token placeholder with your own Runner token.

4. Check the Schedule Trigger time and timezone before activating the workflow.

### 3. Generate Token and Start the Runner

The Runner uses a Bearer token to protect its HTTP endpoint.
Generate the token and start the Runner in the **same PowerShell window**:

```powershell
$env:RUNNER_TOKEN = [guid]::NewGuid().ToString("N")

# To display the token so you can copy it into n8n
$env:RUNNER_TOKEN

# runner.js inherits RUNNER_TOKEN from this process — no need to set it again
node runner.js
```

Keep this PowerShell window open while using the n8n workflow. 
The Runner runs in the foreground, must remain available for scheduled executions, and
invokes `src/scrape.js` and `src/parse.py` from the project root.

Use the same token in both the Runner environment and the n8n HTTP Request
node. If you reopen PowerShell, set RUNNER_TOKEN to the same saved value before starting the Runner again. You do not need to generate a new token unless you intentionally want to rotate it.

```powershell
$env:RUNNER_TOKEN = "YOUR_ACTUAL_RUNNER_TOKEN"
```

In the HTTP Request node, configure:

- **Method**: POST
- **URL**: http://host.docker.internal:3000/run
- **Authentication**: None
- **Send Headers**: Enabled
- **Header Name**: Authorization
- **Header Value**: Bearer **YOUR_ACTUAL_RUNNER_TOKEN**
- **Send Body**: Disabled
- **Timeout**: 600000 milliseconds

Replace **YOUR_ACTUAL_RUNNER_TOKEN** with the token generated on your machine.


### 4. Activate Scheduled Monitoring

Publish or activate the workflow.

Wait for the next scheduled execution.

Check the n8n Executions page for the result.

**Important**: The Windows computer, Docker Desktop, n8n, and Runner must remain running for scheduled monitoring to work. If the Runner stops, n8n cannot execute the scraping and parsing pipeline.

## Files

| File | Purpose |
|------|---------|
| `src/scrape.js` | Playwright script - fetch PDF list, download new PDFs to `downloads/` |
| `src/parse.py` | pdfplumber script - parse PDFs, insert records into `npra.db` |
| `src/explore.js` | One-off script to inspect the NPRA page structure (debug only) |
| `src/test-download.js` | One-off script to test a single PDF download (debug only) |
| `src/check_samples.py` | Random sample inspection of DB rows |
| `src/count_data.py` | Per-DCA row counts |
| `runner.js` | Local HTTP endpoint invoked by n8n |
| `workflow/npra-workflow.json` | Exported n8n workflow configuration |

## Database schema

```sql
CREATE TABLE products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dca             TEXT,
    registration_no TEXT,
    product_name    TEXT,
    holder          TEXT,
    manufacturer    TEXT,
    status          TEXT,
    category        TEXT,
    register_date   TEXT,
    expiry_date     TEXT,
    UNIQUE (registration_no, dca, status)
);
```

The UNIQUE constraint prevents the same `(registration_no, dca, status)` from being inserted twice, while allowing a product to appear with different statuses in the same meeting (e.g. `COS - Approved` and `RE-REGISTRATION (RENEWAL)`).

## Design notes

- **Download detection** — Playwright treats PDF responses as downloads; `page.waitForEvent('download')` is used instead of `response.body()`.
- **Idempotent re-runs** — Both scripts detect existing state before processing:
  - `scrape.js` filters out PDFs already present in `downloads/` (`fs.existsSync`).
  - `parse.py` skips DCAs already present in the database (`SELECT COUNT(*) WHERE dca = ?`).
  - As a safety net, `INSERT OR IGNORE` combined with the `UNIQUE (registration_no, dca, status)` constraint prevents duplicate rows even if the detection step misses something.
- **Table parsing** — Each PDF page is scanned; the header row may or may not be present (continuation pages often skip it). Column indexes are resolved from the header whenever it appears, and reused across subsequent pages of the same file.
- **Whitespace cleanup** — `clean()` collapses newlines and repeated whitespace, and joins hyphenated line breaks (e.g. `RE-\nREGISTRATION` becomes `RE-REGISTRATION`). Enum variants are preserved as they appear in the source PDFs.

## Sample output

![Database screenshot](./samples/db-screenshot.png)

Sample export (3 rows per DCA): [samples/sample-export.csv](./samples/sample-export.csv)

## Output

- `downloads/` — downloaded PDFs, named `DCA404.pdf`, `DCA405.pdf`, ...
- `npra.db` — SQLite database with the `products` table

Both are generated at runtime and excluded from version control via `.gitignore`.