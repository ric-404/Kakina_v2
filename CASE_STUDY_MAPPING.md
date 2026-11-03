# IPT-01 Case Study — Business Process to Program Mapping

**Business:** Kakina Food Products Mfg. (family business, started 2019)

**Proposed program:** Chocolate Ingredient, Recipe, Production, Inventory, Reservation, and Sales Monitoring System

## How the program addresses the documented process

| Interview / documented practice | Implemented feature | Demonstration |
|---|---|---|
| Ingredient quantities and expenses are recorded | Shared ingredient catalog and purchase entries; add new quantities and costs to existing stock | Menu 2 |
| Ingredients may be used in many chocolate products | Each product has a recipe containing ingredient IDs and suggested quantities per unit | Menu 3 |
| Production uses measured ingredients, then the business counts actual finished pouches/bars | Select a product; enter actual weights used; after molding enter counted finished quantity; deduct ingredients and add finished inventory | Menu 4 |
| Expenses are combined over a production day | Record each production run's ingredient usage; daily report sums usage costs across runs on that date | Menu 8 |
| Products are brought in fixed quantities to booths and sold individually | Booth allocation and individual sales | Menus 5 and 7 |
| Unsold booth stock remains available for future selling | Event closing releases remaining allocated stock while documenting any count difference | Menu 5 |
| Messenger reservations specify customer, product and number of items | Reservation records and reserved-stock calculation | Menu 6 |
| Cash / GCash, pickup / delivery | Sales payment labels, reservation fulfillment method, delivery fee | Menus 6 and 7 |
| Owner wants daily sales, best sellers, and sales by location | Date-filtered reports, product totals, and booth/channel summaries | Menu 8 |

## Required integrative-programming features

- **Create (POST):** product, ingredient, purchase, production, booth event, reservation, sale.
- **Read (GET):** products, ingredients, purchases, inventory, recipes (on product records), production, events, reservations, sales, reports.
- **Update (PUT):** product name/price, ingredient name, recipe, booth closing counts, reservation status.
- **Delete (DELETE):** archive product or ingredient while preserving history (HTTP 204).
- **REST API:** FastAPI `/api/*` endpoints with HTTP status codes and JSON bodies.
- **Data exchange:** CLI calls the backend over HTTP using `httpx` with JSON responses. Both persistence and transport use JSON.
- **Validation:** bad prices, invalid dates, duplicate names, impossible ingredient usage, insufficient finished stock and reserved-stock conflicts return useful errors without saving partial changes.

## Suggested 10-minute classroom demonstration

1. Show the five starting chocolate products with no made-up inventory or recipes.
2. Register **Sugar** and **Cacao** as ingredients. Buy 500 g sugar for ₱40, then 500 g for ₱60. Show 1,000 g, ₱100 stock value, ₱0.10/g weighted-average price.
3. In product/recipe management, assign sugar and cacao to Pistachio Chocolate. Explain that the same ingredient can be assigned to other products.
4. Produce Pistachio Chocolate. Enter the **actual** ingredient weights used and the **counted finished pouches**, even if that doesn't match recipe estimates. Show stock deduction and production cost.
5. Create a booth at CLSU, allocate a specific quantity, then record a booth sale.
6. Close the booth and count unsold units. Show that unsold items become available inventory again.
7. Reserve products for a customer using Messenger, then show reserved-stock protection and record a reservation sale.
8. Display reports for that day. Point out the difference between purchases and ingredients consumed in production.
9. Demonstrate HTTP CRUD on `/docs` using a trial product (POST, GET, PUT, DELETE).
10. Show input validation by attempting to use more sugar than is available and entering a negative sales quantity.

**Demo data are examples only.** Actual chocolate recipes must be entered from Kakina's real measurements, not invented for the documentation.

## Known boundaries

The system is a local educational prototype. It has no live Messenger integration, GCash payment processing, full cost accounting, or automatic production yield predictions. Sales revenue minus the cost of ingredients used in production is **not** net profit if finished stock remains or other expenses are not accounted for.

## Modular code explanation for the instructor

- `ui/display.py` is where the border formatting and tables are drawn using `print()`.
- `ui/inputs.py` is where incorrect keyboard inputs are rejected and repeated.
- The remaining files in `ui/` show the respective menus; they use the shared input helpers instead of repeating validation code.
- `api.py` has HTTP routes and Pydantic request models, which call specific functions under `business/`.
- `business/ingredients.py` and `business/production.py` calculate bought/used ingredient quantities and their weighted-average cost.
- `business/inventory.py` and `business/selling.py` handle available stock, reserved stock, event allocations, and completed sales.
- `core.py` validates common data values and writes the JSON file only when the operation succeeds.
- `cli.py` only launches the CLI, so changing a menu does not require editing database rules.

### Improved CLI flow

A production entry is divided into **Select product/date → Actual ingredient usage → Count finished products → Review and confirm**. Each step gets its own bordered section. New purchase, booth, reservation, and sale screens also separate inputs into steps. The system keeps the original FastAPI and JSON behavior while making the terminal UI easier to follow.
