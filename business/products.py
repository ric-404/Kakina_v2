"""Chocolate product catalog management."""

from core import RuleError, next_id, text_value, peso, active_product
from business.inventory import allocated, reserved


def product_add(state, name, price):
    name = text_value(name, "Product name")
    price = peso(price, "Selling price", allow_zero=False)
    if any(p["active"] and p["name"].casefold() == name.casefold()
           for p in state["products"]):
        raise RuleError("An active product with this name already exists.")

    product = {
        "id": next_id(state), "name": name, "price": price,
        "stock": 0, "active": True, "recipe": [],
    }
    state["products"].append(product)
    return product



def product_update(state, product_id, name=None, price=None):
    product = active_product(state, product_id)
    if name is None and price is None:
        raise RuleError("Enter a new name or selling price.")
    if name is not None:
        name = text_value(name, "Product name")
        for other in state["products"]:
            if other["id"] != product_id and other["active"]:
                if other["name"].casefold() == name.casefold():
                    raise RuleError("Another active product already has that name.")
    if price is not None:
        price = peso(price, "Selling price", allow_zero=False)

    if name is not None:
        product["name"] = name
    if price is not None:
        product["price"] = price
    return product



def product_delete(state, product_id):
    product = active_product(state, product_id)
    if product["stock"] != 0:
        raise RuleError("Cannot archive a product that still has stock.")
    if allocated(state, product_id) or reserved(state, product_id):
        raise RuleError("Cannot archive a product with allocations or reservations.")
    product["active"] = False  # Keep older records for reports.
    return product

