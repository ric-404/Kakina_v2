"""Revenue and cost reports and verified physical stock adjustments."""
from ui.display import heading, section, step, show_table, show_summary, notice, warn, success, pesos
from ui.inputs import ask_date, intask, ask_name, confirm
from ui.catalog import inventory


def reports_menu(api):
    heading("Sales and expense reports", "Enter a date, or leave blank for all dates.")
    step(1, "Choose report period")
    day = ask_date("Report date (YYYY-MM-DD; blank = all)", blank_allowed=True)
    report = api.call("GET", "/api/reports", params={"date": day} if day else None)
    section("SALES AND INGREDIENT COST SUMMARY")
    show_summary("Business summary " + (day or "(all dates)"), [
        ("Collected revenue", pesos(report["sales_revenue"])),
        ("Product sales", pesos(report["product_revenue"])),
        ("Delivery fees", pesos(report["delivery_fees"])),
        ("Ingredient purchases paid", pesos(report["ingredient_purchase_expenses"])),
        ("Ingredients used in production", pesos(report["recorded_production_expenses"])),
        ("Revenue less consumed cost", pesos(report["revenue_less_recorded_expenses_not_profit"])),
    ])
    warn("Revenue less ingredient cost is not net profit.")
    show_table(["Product", "Units sold"],
               sorted(report["product_quantities_sold"].items(), key=lambda x: -x[1]),
               "BEST SELLERS")
    show_table(["Booth location", "Revenue"],
               [(name, pesos(value)) for name, value in report["revenue_by_booth"].items()],
               "SALES BY BOOTH")
    show_table(["Sales channel", "Revenue"],
               [(name.title(), pesos(value)) for name, value in report["revenue_by_channel"].items()],
               "SALES BY CHANNEL")
    show_table(["Date", "Revenue"],
               [(name, pesos(value)) for name, value in sorted(report["revenue_by_date"].items())],
               "DAILY REVENUE")
    sales = [r for r in api.call("GET", "/api/sales") if not day or r["date"] == day]
    show_table(["ID", "Date", "Product", "Qty", "Channel", "Total"],
               [(r["id"], r["date"], r["product_name"], r["quantity"],
                 r["channel"], pesos(r["total"])) for r in sales], "SALES HISTORY")
    productions = [r for r in api.call("GET", "/api/production") if not day or r["date"] == day]
    show_table(["ID", "Date", "Units", "Daily expenses"],
               [(r["id"], r["date"], sum(item["quantity"] for item in r["outputs"]),
                 pesos(r["total_cost"])) for r in productions], "PRODUCTION HISTORY")



def adjust_menu(api):
    heading("Verified stock adjustment", "Only correct inventory after checking physical stock.")
    products = inventory(api)
    if not products:
        return
    step(1, "Select product")
    pid = intask("Product ID", allowed={p["id"] for p in products})
    product = next(p for p in products if p["id"] == pid)
    minimum = product["reserved"] + product["allocated"]
    step(2, "Physical inventory count")
    new_stock = intask("Correct stock", minimum=minimum)
    reason = ask_name("Reason for adjustment", max_length=300)
    step(3, "Confirm correction", "Corrections must be based on an actual count.",
         new_page=True, context="Verified inventory adjustment")
    show_summary("Review stock adjustment", [
        ("Product", product["name"]),
        ("Stock", product["stock"]),
        ("Corrected stock", new_stock),
        ("Reason", reason),
    ])
    if confirm("Save stock correction?", default=False):
        row = api.call("POST", "/api/adjustments", {
            "product_id": pid, "new_stock": new_stock, "reason": reason,
        })
        success(f"Stock adjusted from {row['old_stock']} to {row['new_stock']} units.")

