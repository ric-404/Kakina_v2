"""Record actual ingredient use and count finished chocolates."""

from decimal import Decimal
from core import (RuleError, next_id, active_product, whole_number, valid_date,
                  optional_text, decimal_amount, as_decimal)
from business.ingredients import active_ingredient


def produce(state, production_date, product_id, ingredients_used, finished_quantity, note=""):
    """One product run. Sum run costs by date in the daily report.

    Actual ingredient amounts are measured before packaging. The number of
    finished items is counted afterward, not predicted from a recipe.
    """
    production_date = valid_date(production_date)
    product = active_product(state, product_id)
    finished_quantity = whole_number(finished_quantity, "Finished product count")
    note = optional_text(note)
    if not product["recipe"]:
        raise RuleError("Set this product's recipe before recording production.")
    if not isinstance(ingredients_used, list) or not ingredients_used:
        raise RuleError("Enter the ingredients actually used in production.")

    allowed = {x["ingredient_id"] for x in product["recipe"]}
    used_ids = set()
    lines = []
    for item in ingredients_used:
        iid = item.get("ingredient_id")
        row = active_ingredient(state, iid)
        if iid not in allowed:
            raise RuleError(f"{row['name']} is not in this product's recipe.")
        if iid in used_ids:
            raise RuleError("Enter each ingredient only once.")
        used_ids.add(iid)
        amount = decimal_amount(item.get("quantity"), "Amount used",
                                places=3 if row["unit"] == "g" else 0)
        old_qty = as_decimal(row["quantity"])
        if amount > old_qty:
            raise RuleError(f"Not enough {row['name']}: {old_qty} {row['unit']} in stock.")
        # Weighted-average cost of the remaining ingredient stock.
        cost = (as_decimal(row["stock_value"]) * amount / old_qty).quantize(
            Decimal("0.01"), rounding="ROUND_HALF_UP")
        if amount == old_qty:
            cost = as_decimal(row["stock_value"])
        lines.append({"ingredient_id": iid, "name": row["name"],
                      "quantity": float(amount) if row["unit"] == "g" else int(amount),
                      "unit": row["unit"], "cost": float(cost)})

    if used_ids != allowed:
        missing = [active_ingredient(state, i)["name"] for i in allowed - used_ids]
        raise RuleError("Enter actual usage for every recipe ingredient: " + ", ".join(missing))

    # All validation has passed. Apply the stock movements together.
    for line in lines:
        row = active_ingredient(state, line["ingredient_id"])
        new_qty = as_decimal(row["quantity"]) - as_decimal(line["quantity"])
        new_value = as_decimal(row["stock_value"]) - as_decimal(line["cost"])
        row["quantity"] = float(new_qty) if row["unit"] == "g" else int(new_qty)
        row["stock_value"] = round(float(max(Decimal("0"), new_value)), 2)
        if new_qty == 0:
            row["stock_value"] = 0.0

    product["stock"] += finished_quantity
    record = {"id": next_id(state), "date": production_date,
              "product_id": product_id, "product_name": product["name"],
              "ingredients_used": lines, "total_cost": round(sum(x["cost"] for x in lines), 2),
              "finished_quantity": finished_quantity,
              # Store output in old-compatible shape for history screens.
              "outputs": [{"product_id": product_id, "quantity": finished_quantity}],
              "note": note}
    state["production"].append(record)
    return record

