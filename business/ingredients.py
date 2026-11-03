"""Reusable ingredient catalog, buying history and suggested recipes."""
from decimal import Decimal

from core import (RuleError, get, next_id, text_value, valid_choice,
                  active_product, peso, valid_date, optional_text,
                  decimal_amount, as_decimal)


def ingredient_add(state, name, unit):
    name = text_value(name, "Ingredient name")
    unit = valid_choice(unit, ("g", "pcs"), "Ingredient unit")
    if any(i["active"] and i["name"].casefold() == name.casefold()
           for i in state["ingredients"]):
        raise RuleError("An active ingredient with this name already exists.")
    row = {"id": next_id(state), "name": name, "unit": unit,
           "quantity": 0, "stock_value": 0.0, "active": True}
    state["ingredients"].append(row)
    return row



def active_ingredient(state, ingredient_id):
    ingredient = get(state, "ingredients", ingredient_id)
    if not ingredient["active"]:
        raise RuleError("This ingredient is archived.")
    return ingredient



def ingredient_update(state, ingredient_id, name):
    row = active_ingredient(state, ingredient_id)
    name = text_value(name, "Ingredient name")
    if any(i["active"] and i["id"] != ingredient_id and
           i["name"].casefold() == name.casefold() for i in state["ingredients"]):
        raise RuleError("An active ingredient with this name already exists.")
    row["name"] = name
    return row



def ingredient_delete(state, ingredient_id):
    row = active_ingredient(state, ingredient_id)
    if row["quantity"] != 0:
        raise RuleError("Cannot archive an ingredient with remaining stock.")
    for product in state["products"]:
        if product["active"] and any(x["ingredient_id"] == ingredient_id for x in product["recipe"]):
            raise RuleError("Remove this ingredient from active product recipes first.")
    row["active"] = False
    return row



def purchase_add(state, ingredient_id, quantity, total_cost, purchase_date, note=""):
    """Add purchased quantity and value, keeping weighted-average costing."""
    row = active_ingredient(state, ingredient_id)
    quantity = decimal_amount(quantity, "Purchased quantity", places=3 if row["unit"] == "g" else 0)
    cost = peso(total_cost, "Total purchase cost", allow_zero=False)
    purchase_date = valid_date(purchase_date)
    note = optional_text(note)
    previous_qty = as_decimal(row["quantity"])
    new_qty = previous_qty + quantity
    row["quantity"] = float(new_qty) if row["unit"] == "g" else int(new_qty)
    row["stock_value"] = float(as_decimal(row["stock_value"]) + as_decimal(cost))
    record = {"id": next_id(state), "date": purchase_date,
              "ingredient_id": ingredient_id, "quantity": float(quantity) if row["unit"] == "g" else int(quantity),
              "unit": row["unit"], "total_cost": cost, "note": note}
    state["purchases"].append(record)
    return record



def ingredient_inventory(state):
    result = []
    for row in state["ingredients"]:
        if row["active"]:
            avg = (as_decimal(row["stock_value"]) / as_decimal(row["quantity"])
                   if row["quantity"] else Decimal("0"))
            result.append({**row, "average_unit_cost": round(float(avg), 4)})
    return result



def recipe_set(state, product_id, items):
    """Store suggested ingredient amounts PER finished pouch/bar.

    These are only a recipe reference. Actual production uses quantities weighed
    by the owner, never guessed from the number of finished products.
    """
    product = active_product(state, product_id)
    if not isinstance(items, list) or not items:
        raise RuleError("Add at least one ingredient to the product recipe.")
    seen = set()
    recipe = []
    for item in items:
        iid = item.get("ingredient_id")
        ingredient = active_ingredient(state, iid)
        if iid in seen:
            raise RuleError("The same ingredient appears twice in this recipe.")
        seen.add(iid)
        amount = decimal_amount(item.get("quantity"), "Recipe amount",
                                places=3 if ingredient["unit"] == "g" else 0)
        recipe.append({"ingredient_id": iid,
                       "quantity": float(amount) if ingredient["unit"] == "g" else int(amount)})
    product["recipe"] = recipe
    return product

