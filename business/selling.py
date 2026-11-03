"""Booth events, reservations and completed transactions."""

from datetime import date as CalendarDate
from core import (RuleError, get, next_id, text_value, valid_date,
                  whole_number, valid_choice, active_product, peso, optional_text)
from business.inventory import free_stock, allocated


def event_open(state, name, event_date, allocations):
    name = text_value(name, "Booth location")
    event_date = valid_date(event_date)
    if not isinstance(allocations, list) or not allocations:
        raise RuleError("Choose at least one product for the booth.")

    chosen = {}
    for item in allocations:
        product = active_product(state, item["product_id"])
        count = whole_number(item["quantity"])
        key = str(product["id"])
        chosen[key] = chosen.get(key, 0) + count

    for key, quantity in chosen.items():
        if quantity > free_stock(state, int(key)):
            raise RuleError(f"Not enough free stock for product #{key}.")

    event = {
        "id": next_id(state), "name": name, "date": event_date,
        "status": "open", "allocations": chosen, "sold": {},
        "physical_remaining": {}, "differences": {},
    }
    state["events"].append(event)
    return event



def event_close(state, event_id, counts):
    event = get(state, "events", event_id)
    if event["status"] != "open":
        raise RuleError("This booth event is already closed.")
    if not isinstance(counts, list):
        raise RuleError("Physical counts must be a list.")

    expected = {}
    for key, quantity in event["allocations"].items():
        expected[key] = quantity - event["sold"].get(key, 0)

    actual = {}
    for item in counts:
        key = str(item["product_id"])
        if key in actual:
            raise RuleError("Each booth product should be counted only once.")
        actual[key] = whole_number(item["quantity"], "Actual count", allow_zero=True)

    if set(actual) != set(expected):
        raise RuleError("Provide a physical count for every allocated booth product.")

    differences = {}
    for key, count in actual.items():
        differences[key] = count - expected[key]

    event["physical_remaining"] = actual
    event["differences"] = differences
    event["status"] = "closed"
    # Do not automatically change stock if counting doesn't match sales records.
    return {"event": event, "expected": expected, "differences": differences}



def reservation_add(state, customer, product_id, quantity, method="pickup", date=None):
    customer = text_value(customer, "Customer name")
    product = active_product(state, product_id)
    quantity = whole_number(quantity)
    method = valid_choice(method, ("pickup", "delivery"), "Fulfillment method")
    reservation_date = valid_date(date or CalendarDate.today().isoformat())

    if quantity > free_stock(state, product_id):
        raise RuleError("Not enough free stock for this reservation.")

    record = {
        "id": next_id(state), "customer": customer,
        "product_id": product_id, "quantity": quantity,
        "method": method, "date": reservation_date,
        "status": "reserved",
    }
    state["reservations"].append(record)
    return record



def reservation_cancel(state, reservation_id):
    reservation = get(state, "reservations", reservation_id)
    if reservation["status"] != "reserved":
        raise RuleError("Only active reservations can be cancelled.")
    reservation["status"] = "cancelled"
    return reservation



def sale_add(state, product_id, quantity, channel="direct", event_id=None,
             reservation_id=None, payment="cash", date=None, delivery_fee=0,
             customer=""):
    product = active_product(state, product_id)
    quantity = whole_number(quantity)
    channel = valid_choice(channel, ("direct", "messenger", "booth", "reservation"), "Sales channel")
    payment = valid_choice(payment, ("cash", "gcash"), "Payment method")
    delivery_fee = peso(delivery_fee, "Delivery fee")
    sale_date = valid_date(date or CalendarDate.today().isoformat())
    customer = optional_text(customer, "Customer name", 100)

    event = None
    reservation = None
    if channel == "booth":
        if event_id is None:
            raise RuleError("Choose an open booth event.")
        event = get(state, "events", event_id)
        if event["status"] != "open":
            raise RuleError("This booth is already closed.")
        key = str(product_id)
        left_at_booth = event["allocations"].get(key, 0) - event["sold"].get(key, 0)
        if quantity > left_at_booth:
            raise RuleError("Not enough products left at this booth.")
    elif channel == "reservation":
        if reservation_id is None:
            raise RuleError("Choose a reservation to complete.")
        reservation = get(state, "reservations", reservation_id)
        if reservation["status"] != "reserved":
            raise RuleError("Reservation is already completed or cancelled.")
        if reservation["product_id"] != product_id or reservation["quantity"] != quantity:
            raise RuleError("Product and quantity must match the reservation.")
        if quantity > product["stock"] - allocated(state, product_id):
            raise RuleError("Not enough physical stock for this reservation.")
        customer = reservation["customer"]
    else:
        if quantity > free_stock(state, product_id):
            raise RuleError("Not enough free stock for this sale.")

    if quantity > product["stock"]:
        raise RuleError("Not enough physical stock for this sale.")

    subtotal = round(quantity * product["price"], 2)
    record = {
        "id": next_id(state), "date": sale_date,
        "product_id": product_id, "product_name": product["name"],
        "quantity": quantity, "unit_price": product["price"],
        "subtotal": subtotal, "delivery_fee": delivery_fee,
        "total": round(subtotal + delivery_fee, 2),
        "channel": channel, "payment": payment, "customer": customer,
        "event_id": event["id"] if event else None,
        "reservation_id": reservation["id"] if reservation else None,
    }

    state["sales"].append(record)
    product["stock"] -= quantity
    if event:
        key = str(product_id)
        event["sold"][key] = event["sold"].get(key, 0) + quantity
    if reservation:
        reservation["status"] = "completed"
    return record

