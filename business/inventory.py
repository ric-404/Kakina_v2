"""Finished-product stock, booth allocations and physical adjustments."""

from datetime import date as CalendarDate
from core import RuleError, get, next_id, whole_number, text_value


def reserved(state, product_id):
    total = 0
    for record in state["reservations"]:
        if record["product_id"] == product_id and record["status"] == "reserved":
            total += record["quantity"]
    return total



def allocated(state, product_id):
    total = 0
    key = str(product_id)
    for event in state["events"]:
        if event["status"] == "open":
            brought = event["allocations"].get(key, 0)
            sold = event["sold"].get(key, 0)
            total += brought - sold
    return total



def free_stock(state, product_id):
    product = get(state, "products", product_id)
    return product["stock"] - reserved(state, product_id) - allocated(state, product_id)



def inventory(state):
    rows = []
    for product in state["products"]:
        if product["active"]:
            rows.append({
                **product,
                "allocated": allocated(state, product["id"]),
                "reserved": reserved(state, product["id"]),
                "available": free_stock(state, product["id"]),
            })
    return rows



def adjust(state, product_id, new_stock, reason):
    product = active_product(state, product_id)
    new_stock = whole_number(new_stock, "Physical stock", allow_zero=True)
    reason = text_value(reason, "Reason", max_length=300)
    minimum = reserved(state, product_id) + allocated(state, product_id)
    if new_stock < minimum:
        raise RuleError(f"Stock cannot be lower than reserved/booth stock ({minimum}).")

    record = {
        "id": next_id(state), "date": CalendarDate.today().isoformat(),
        "product_id": product_id,
        "old_stock": product["stock"], "new_stock": new_stock,
        "reason": reason,
    }
    product["stock"] = new_stock
    state["adjustments"].append(record)
    return record

