# Kakina Food Products Mfg. — Modular CLI System

**Student-style Python CLI + FastAPI + JSON. No Rich and no SQL database required.**

This project follows the business process described in the Kakina interview. It is a **terminal application**, not a web-based UI. The CLI sends HTTP requests to FastAPI, which validates business operations and saves the records to `kakina_data.json`.

## 1. Install and run (Windows or Linux)

**Before starting:** Install Python, download/extract the project, and open a terminal in the folder containing `cli.py` and `requirements.txt`. On Windows, check Python with `py --version`; on Linux, use `python --version`.

### Windows 10/11 — PowerShell or Command Prompt

Open the project folder in File Explorer, click the address bar, type `powershell` (or `cmd`), and press Enter. Then run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe cli.py
```

These commands also work in Command Prompt. They use the virtual environment's Python directly, so **you do not have to activate the virtual environment** or change PowerShell's execution policy.

To run the program again later, open a terminal in the same folder and run:

```powershell
.\.venv\Scripts\python.exe cli.py
```

If `py` is not recognized, try `python -m venv .venv` (if Python is installed), or install Python and reopen the terminal.

### Arch Linux - Fish shell

Open a terminal inside the project directory and run:

```fish
python -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements.txt
python cli.py
```

If you use bash/zsh, activate with `source .venv/bin/activate`. Run `deactivate` to leave an activated virtual environment.

### How the program starts

`cli.py` automatically starts the local FastAPI server and then opens the terminal menus. There is no need to open a separate API terminal for normal use. The CLI is plain text, without colors, Rich, or `textwrap`; menus clear automatically during normal interaction.

While the CLI is running, open **http://127.0.0.1:8765/docs** to explore the FastAPI endpoints in a browser.

### Useful commands

| Task | Windows PowerShell / Command Prompt | Linux (activated venv) |
|---|---|---|
| Start CLI | `.\.venv\Scripts\python.exe cli.py` | `python cli.py` |
| Run tests | `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` | `python -m unittest discover -s tests -v` |
| Start API only | `.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8765` | `python -m uvicorn api:app --host 127.0.0.1 --port 8765` |
| Connect CLI to running API | `.\.venv\Scripts\python.exe cli.py --connect` | `python cli.py --connect` |

**Manual API demo:** Run the **Start API only** command in one terminal; open a second terminal in the same project directory and run **Connect CLI to running API**. Do not start two API servers on the same port.

## 2. Code organization — where to make changes

```text
Kakina_Modular_FastAPI_CLI_ASCII/
├── cli.py                  # Only starts the terminal program
├── api.py                  # FastAPI routes and request schemas
├── core.py                 # Shared validation and safe JSON read/write
├── business/
│   ├── ingredients.py      # Ingredients, purchases, weighted cost, recipes
│   ├── products.py         # Product CRUD and archiving
│   ├── production.py       # Measured ingredient use and finished counts
│   ├── inventory.py        # Finished stock, reserved and allocated stock
│   ├── selling.py          # Booth events, reservations, sales
│   └── reports.py          # Sales, ingredient costs and business summaries
├── ui/
│   ├── display.py          # Borders, titles, tables, section headings
│   ├── inputs.py           # Validated input(), amounts, dates, confirmations
│   ├── client.py           # Sends requests to the FastAPI server
│   ├── catalog.py          # Ingredient/product/recipe CLI menus
│   ├── production.py       # Step-by-step production CLI screen
│   ├── selling.py          # Booth/reservation/sales CLI screens
│   ├── reports.py          # Reports and adjustments CLI screens
│   └── menu.py             # Main dashboard and navigation
├── tests/                  # Automated API, validation, and UI tests
├── requirements.txt
├── CASE_STUDY_MAPPING.md
└── kakina_data.json        # Created automatically after the first change
```

**Editing guide:**

| You want to change ... | Start with ... |
|---|---|
| Border design or spacing | `ui/display.py` |
| Input prompts or input validation in terminal | `ui/inputs.py` |
| Main menu numbers/labels | `ui/menu.py` |
| Ingredient purchasing screen | `ui/catalog.py` |
| Recipe creation screen | `ui/catalog.py` |
| Production screen | `ui/production.py` |
| Ingredient deductions / cost calculation | `business/production.py` |
| Ingredient purchasing and average pricing | `business/ingredients.py` |
| Booth and reservation rules | `business/selling.py` |
| How reports are calculated | `business/reports.py` |
| REST endpoints or JSON request models | `api.py` |
| Loading and saving JSON safely | `core.py` |

**How the parts connect:** `ui/` collects information -> `ui/client.py` sends HTTP + JSON -> `api.py` calls a `business/` function -> `core.py` saves the changes to JSON. The CLI never edits JSON directly.

## 3. Readable terminal layout

The CLI uses standard Python `print()` and `input()` with reusable ASCII border functions in `ui/display.py`. Only long product, ingredient, customer, and location names wrap inside tables; other columns stay on one line. On narrow terminals, the table becomes a series of bordered records. New main menus clear the previous terminal view, and key input stages (such as production counting and confirmation) open fresh screens. A confirmation screen repeats the important information before saving. **No Rich library is needed.**

To change borders, edit `border()`, `show_table()`, or `show_summary()` in `ui/display.py`. `clear_screen()` uses `cls` on Windows and `clear` on Linux/macOS. It is called when a new menu or major step opens. Redirected output is not cleared; there is no flag to disable screen clearing.

Example:

```text
  +--------------------------------------------------------+
  | STEP 1 - SELECT PRODUCT AND DATE                       |
  +--------------------------------------------------------+

  Product ID to produce: 2

  +--------------------------------------------------------+
  | STEP 2 - ENTER ACTUAL INGREDIENT USAGE                  |
  | The recipe is a guide; enter actual amounts weighed.   |
  +--------------------------------------------------------+

  +--------------------------------------------------------+
  | INGREDIENT: SUGAR                                      |
  | Available: 1000 g                                      |
  +--------------------------------------------------------+

  Actual Sugar used (g): 300

  +--------------------------------------------------------+
  | STEP 3 - COUNT MOLDED AND PACKAGED CHOCOLATES          |
  +--------------------------------------------------------+

  Actual finished pouches/bars counted: 20

  +--------------------------------------------------------+
  | STEP 4 - REVIEW BEFORE SAVING                          |
  +--------------------------------------------------------+

  Deduct ingredients and add finished products (y/n):
```

Example values above are **not** Kakina's real recipe or production records.

## 4. Daily workflow — recommended order

1. **Menu 2: Ingredients and Purchases.** Register reusable ingredients such as cacao, sugar, pistachios and mango. Use grams (`g`) for weighted ingredients or pieces (`pcs`) for packaging. Record purchased quantity and *total paid*. A purchase adds to existing stock and recalculates weighted-average unit cost.
2. **Menu 3: Products and Recipes.** The five interview-listed chocolate products are preloaded with zero stock and **empty recipes**. Add or edit an ingredient list for each product. Ingredients can be reused across many chocolate products. Suggested recipe quantities are entered *per pouch/bar* and are only a reference.
3. **Menu 4: Production.** Choose the product, then enter **actual amounts of every recipe ingredient used** in the mixture. After molding, enter the **actual count** of finished pouches/bars. Review before saving. The server reduces ingredient stocks and increases finished product stock in the same successful transaction.
4. **Menu 5: Booth Events.** Allocate a number of finished chocolates to a booth at Talavera, CLSU, etc. Individual booth sales are recorded in menu 7. At closing, count leftovers. The system compares actual and expected counts and releases unsold allocations for future selling. Differences are flagged for review rather than automatically changing physical stock.
5. **Menu 6: Reservations.** Enter who reserved which product, quantity, date, and pickup/delivery method. Reserved quantities cannot be sold through other channels.
6. **Menu 7: Individual Sales.** Record direct, Messenger, booth, or reservation sales. Add payment label (cash/GCash) and optional delivery charge. Sales deduct finished-product inventory.
7. **Menu 8: Reports.** Review daily/overall sales, product quantities sold, selling locations, ingredient purchases, and ingredient costs used during production.
8. **Menu 9: Verified Inventory Adjustment.** Correct finished-product stock after a physical check and supply a reason. You cannot reduce stock below quantities already reserved or allocated to booths.

## 5. Production and costing behavior

**Chosen workflow: measured usage then finished count.** The saved recipe is displayed to help the owner, but the system does **not** multiply recipe weight by finished product count to deduct inventory. Production records the weight or piece count actually used. A single ingredient (such as sugar) belongs to one inventory record even when shared by multiple recipes.

**Weighted-average example (demonstration only):** Buy 500 g sugar for ₱40 and another 500 g for ₱60. Stock is 1,000 g with a value of ₱100. Using 300 g costs ₱30 at the current average and leaves 700 g in stock. Count the finished pouches after molding; don't try to predict the yield from the recipe.

**Daily expenses:** Multiple runs can be recorded separately, but the daily report sums their *actual ingredient usage costs*. Purchases are reported separately. Subtracting today's ingredient usage cost from today's sales revenue is **not** true net profit if some produced items are unsold or other costs aren't included.

## 6. Validation and protection

- Menu choices, record IDs, dates, whole quantities, gram weights, and money amounts are checked. Invalid answers cause another prompt rather than crashing the menu.
- Negative/zero purchases, invalid costs, non-existent ingredient IDs, duplicate active names, and repeated ingredients in one recipe are rejected.
- Production requires all recipe ingredients, measured amounts and sufficient available ingredient stock. If validation fails, **no stock or production record is saved**.
- Selling more than available stock, booth stock, or reserved stock is prohibited. A completed/cancelled reservation cannot be sold again.
- Product names, customer names and notes cannot include control characters that could break terminal display.
- All mutation requests pass through the server. JSON is written to a temporary file first, then atomically replaced. A damaged JSON file produces an error instead of silently resetting records.

The code is intended for a **single-user local academic project**, not a commercial multi-user deployment; no program can be guaranteed completely error-proof.

## 7. API requirement (IPT-01)

The CLI uses FastAPI even though its main interface is terminal-based. Example endpoints:

| HTTP method | Route | Purpose |
|---|---|---|
| GET / POST | `/api/products` | Read/create chocolate products |
| PUT / DELETE | `/api/products/{id}` | Edit/archive a product |
| GET / POST | `/api/ingredients` | Read/register ingredients |
| PUT / DELETE | `/api/ingredients/{id}` | Rename/archive an ingredient |
| GET / POST | `/api/purchases` | View/record ingredient purchases |
| PUT | `/api/products/{id}/recipe` | Create/replace a recipe |
| GET / POST | `/api/production` | View/save production |
| GET / POST | `/api/events` | View/open booth events |
| PUT | `/api/events/{id}/close` | Close and reconcile a booth |
| GET / POST | `/api/reservations` | View/create reservations |
| PUT | `/api/reservations/{id}/cancel` | Cancel a reservation |
| GET / POST | `/api/sales` | View/record individual sales |
| GET | `/api/inventory`, `/api/reports` | View remaining stock and reports |

Try GET, POST, PUT, DELETE at **http://127.0.0.1:8765/docs** for your live CRUD demo. Deletes *archive* entries instead of erasing historical records, returning HTTP **204** on success.

## 8. Testing and JSON data

Run automated tests from the project directory:

**Windows (PowerShell or Command Prompt):**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Linux (Fish with virtual environment activated):**

```fish
python -m unittest discover -s tests -v
```

Tests use temporary JSON files, so your real records are unchanged. The tests check API CRUD, JSON data persistence, calculated ingredient costs, recipes, stock rules, reservations, events, input validation, and terminal borders.

The program creates `kakina_data.json` in the project directory after the first saved operation. To use a separate demo data file, set `KAKINA_DATA` **before** launching the CLI:

**Windows PowerShell:**

```powershell
$env:KAKINA_DATA = "$PWD\kakina_demo.json"
.\.venv\Scripts\python.exe cli.py
Remove-Item Env:KAKINA_DATA
```

The `Remove-Item` command clears the variable after you have closed the CLI, so later launches can use the normal data file.

**Windows Command Prompt:**

```bat
set "KAKINA_DATA=%CD%\kakina_demo.json"
.\.venv\Scripts\python.exe cli.py
set KAKINA_DATA=
```

**Linux Fish:**

```fish
set -x KAKINA_DATA "$PWD/kakina_demo.json"
python cli.py
set -e KAKINA_DATA
```

**Important:** If upgrading from an older Kakina ZIP, back up your old `kakina_data.json` first. The app supports some older records, but it cannot invent missing ingredient purchase history or retroactively deduct ingredient usage. Your original data is never included in this ZIP.

### Limits

- No live Messenger integration, real GCash processing, barcode checkout, or customer payment collection.
- No expiration tracking, yield estimation, inventory valuation per finished product, or full net-profit accounting.
- Single-user local JSON storage; do not run multiple independent API server processes against one data file.

## 9. Windows troubleshooting

- **`py` is not recognized:** Check whether Python is installed. Try `python --version`; if that works, use `python -m venv .venv` for the first command instead.
- **PowerShell says scripts are disabled:** Use `.\.venv\Scripts\python.exe` as shown above. Activating the environment is optional, so you do not need to change the execution policy.
- **`No module named fastapi` or `No module named requests`:** Install dependencies using `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and use that same Python to start `cli.py`.
- **API connection or port error:** Normally launch only `cli.py`, which starts the API itself. If you manually start the API, run the CLI with `--connect` in a second terminal rather than starting another server.
- **Missing `requirements.txt` or `cli.py`:** Make sure your terminal is opened inside the extracted project folder, not its parent directory.

**Platform note:** These are Windows setup instructions based on the documented CLI and Python dependencies. The actual project source files were not included with this README, so Windows execution has not been tested here.
