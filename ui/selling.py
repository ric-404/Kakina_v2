"""Booth events, reservations, and sales screens."""
from ui.display import heading, section, step, notice, success, warn, show_table, show_summary, pesos
from ui.inputs import (ask_name, ask_optional, ask_date, intask, moneyask,
                       choose, confirm, action_menu)
from ui.catalog import inventory, select_products


def booths_menu(api):
    heading("Booth events", "Allocate products, sell them, and count leftovers after the event.")
    events = api.call("GET", "/api/events")
    show_table(["ID", "Date", "Location", "Status"],
               [(e["id"], e["date"], e["name"], e["status"]) for e in events],
               "EVENT RECORDS")
    action = action_menu([
        ("open", "Open new booth event"),
        ("close", "Close event and count remaining stock"),
    ])
    if action == "open":
        step(1, "Event details")
        location = ask_name("Event location")
        day = ask_date("Event date (YYYY-MM-DD)")
        step(2, "Allocate products to booth")
        allocations = select_products(api, "Products to bring to the booth", check_stock=True)
        if not allocations:
            warn("No products selected. Event not created.")
            return
        step(3, "Confirm booth allocation", new_page=True,
             context=f"Booth event: {location}")
        show_table(["Product", "Quantity"],
                   [(next((p["name"] for p in api.call("GET", "/api/products")
                           if p["id"] == x["product_id"]), x["product_id"]), x["quantity"])
                    for x in allocations], "PRODUCTS TO BRING")
        if confirm(f"Open booth event at {location}?"):
            row = api.call("POST", "/api/events", {
                "name": location, "date": day, "allocations": allocations,
            })
            success(f"Booth #{row['id']} opened. Products are allocated, not yet sold.")
    elif action == "close":
        active = [e for e in events if e["status"] == "open"]
        if not active:
            notice("No open booth events to close.")
            return
        step(1, "Select open booth")
        show_table(["ID", "Location", "Date"],
                   [(e["id"], e["name"], e["date"]) for e in active],
                   "OPEN BOOTH EVENTS")
        eid = intask("Open event ID", allowed={e["id"] for e in active})
        event = next(e for e in active if e["id"] == eid)
        names = {str(p["id"]): p["name"] for p in api.call("GET", "/api/products")}
        counts = []
        step(2, "Count unsold chocolates", "Count the remaining products physically after the event.")
        for pid, brought in event["allocations"].items():
            sold = event["sold"].get(pid, 0)
            expected = brought - sold
            show_summary(names.get(pid, "Product #" + pid), [
                ("Brought to booth", brought),
                ("Recorded as sold", sold),
                ("Expected remaining", expected),
            ])
            count = intask("Physically counted remaining stock", expected, minimum=0)
            counts.append({"product_id": int(pid), "quantity": count})
        step(3, "Confirm closing counts", new_page=True,
             context=f"Closing booth: {event['name']}")
        show_table(["Product", "Counted remaining"],
                   [(names.get(str(c["product_id"]), c["product_id"]), c["quantity"])
                    for c in counts], "PHYSICAL COUNT REVIEW")
        if not confirm("Close booth with these physical counts?"):
            return
        result = api.call("PUT", f"/api/events/{eid}/close", {"counts": counts})
        show_table(["Product", "Expected", "Counted", "Difference"],
                   [(names.get(pid, pid), expected,
                     result["event"]["physical_remaining"][pid], result["differences"][pid])
                    for pid, expected in result["expected"].items()], "STOCK RECONCILIATION")
        if any(result["differences"].values()):
            warn("There is a mismatch. Check records before making a verified stock correction.")
        else:
            success("Booth closed. Unsold products can be sold again later.")



def reservations_menu(api):
    heading("Customer reservations", "Record who reserved which product and how many.")
    rows = api.call("GET", "/api/reservations")
    names = {p["id"]: p["name"] for p in api.call("GET", "/api/products")}
    show_table(["ID", "Customer", "Product", "Qty", "Method", "Status"],
               [(r["id"], r["customer"], names.get(r["product_id"], r["product_id"]),
                 r["quantity"], r["method"], r["status"]) for r in rows],
               "RESERVATIONS")
    action = action_menu([
        ("add", "New reservation"),
        ("cancel", "Cancel reservation and release reserved stock"),
    ])
    if action == "add":
        step(1, "Select products to reserve")
        products = inventory(api)
        allowed = {p["id"]: p["available"] for p in products if p["available"] > 0}
        if not allowed:
            warn("No available stock to reserve. Record production first.")
            return
        pid = intask("Product ID", allowed=set(allowed))
        qty = intask("Quantity to reserve", maximum=allowed[pid])
        step(2, "Customer and fulfillment details", new_page=True,
             context="New customer reservation")
        customer = ask_name("Customer name")
        method = choose("Pickup or delivery", ["pickup", "delivery"], "pickup")
        day = ask_date("Reservation date")
        step(3, "Confirm reservation", new_page=True,
             context="Reservation confirmation")
        product_name = next((p["name"] for p in products if p["id"] == pid), str(pid))
        show_summary("Review reservation", [
            ("Customer", customer), ("Product", product_name),
            ("Quantity", qty), ("Method", method), ("Date", day)])
        if confirm("Save reservation?"):
            row = api.call("POST", "/api/reservations", {
                "customer": customer, "product_id": pid, "quantity": qty,
                "method": method, "date": day,
            })
            success(f"Reservation #{row['id']} saved. {qty} units reserved for {customer}.")
    elif action == "cancel":
        active_ids = {r["id"] for r in rows if r["status"] == "reserved"}
        if not active_ids:
            notice("There are no active reservations.")
            return
        show_table(["ID", "Customer", "Product", "Qty"],
                   [(r["id"], r["customer"], names.get(r["product_id"], r["product_id"]),
                     r["quantity"]) for r in rows if r["status"] == "reserved"],
                   "ACTIVE RESERVATIONS")
        rid = intask("Active reservation ID", allowed=active_ids)
        if confirm(f"Cancel reservation #{rid}?", default=False):
            row = api.call("PUT", f"/api/reservations/{rid}/cancel")
            success(f"Reservation #{row['id']} cancelled; stock released.")



def sales_menu(api):
    heading("Record a completed sale", "A sale reduces inventory when saved.")
    step(1, "Sales information")
    channel = choose("Sales channel", ["booth", "messenger", "direct", "reservation"], "booth")
    day = ask_date("Sale date (YYYY-MM-DD)")
    payment = choose("Payment method", ["cash", "gcash"], "cash")
    data = {"channel": channel, "date": day, "payment": payment}

    step(2, "Choose the products being sold")
    if channel == "booth":
        open_events = [e for e in api.call("GET", "/api/events") if e["status"] == "open"]
        if not open_events:
            warn("There is no open booth. Start an event in menu 4 first.")
            return
        show_table(["ID", "Location", "Date"],
                   [(e["id"], e["name"], e["date"]) for e in open_events], "OPEN BOOTHS")
        data["event_id"] = intask("Open event ID", allowed={e["id"] for e in open_events})

    if channel == "reservation":
        reservations = [r for r in api.call("GET", "/api/reservations")
                        if r["status"] == "reserved"]
        if not reservations:
            warn("No active reservations. Create one in menu 5 first.")
            return
        names = {p["id"]: p["name"] for p in api.call("GET", "/api/products")}
        show_table(["ID", "Customer", "Product", "Qty"],
                   [(r["id"], r["customer"], names.get(r["product_id"], r["product_id"]),
                     r["quantity"]) for r in reservations], "ACTIVE RESERVATIONS")
        rid = intask("Reservation ID", allowed={r["id"] for r in reservations})
        reservation = next(r for r in reservations if r["id"] == rid)
        data["reservation_id"] = rid
        data["product_id"] = reservation["product_id"]
        data["quantity"] = reservation["quantity"]
        notice(f"Completing all {reservation['quantity']} units for {reservation['customer']}.")
    else:
        products = inventory(api)
        if channel == "booth":
            event = next(e for e in open_events if e["id"] == data["event_id"])
            limits = {int(pid): amount - event["sold"].get(pid, 0)
                      for pid, amount in event["allocations"].items()
                      if amount - event["sold"].get(pid, 0) > 0}
        else:
            limits = {p["id"]: p["available"] for p in products if p["available"] > 0}
        if not limits:
            warn("No available stock for this sales channel.")
            return
        data["product_id"] = intask("Product ID", allowed=set(limits))
        data["quantity"] = intask("Quantity sold", maximum=limits[data["product_id"]])
        data["customer"] = ask_optional("Customer name (optional)", 100)
    step(3, "Payment and delivery", new_page=True,
         context=f"Sale: {channel}")
    data["delivery_fee"] = moneyask("Delivery fee (₱, 0 if none)", 0)
    product = next((p for p in api.call("GET", "/api/products")
                    if p["id"] == data["product_id"]), None)
    step(4, "Review sale", "Saving deducts the sold products from finished inventory.",
         new_page=True, context="Sales confirmation")
    if product:
        subtotal = product["price"] * data["quantity"]
        show_summary("Review sale", [
            ("Product", product["name"]),
            ("Quantity", data["quantity"]),
            ("Product subtotal", pesos(subtotal)),
            ("Delivery fee", pesos(data["delivery_fee"])),
            ("Expected total", pesos(subtotal + data["delivery_fee"])),
        ])
    if confirm("Save sale and update inventory?"):
        result = api.call("POST", "/api/sales", data)
        success(f"Sale #{result['id']} recorded. Collected {pesos(result['total'])}.")

