"""Products, reusable ingredients, purchasing, and recipes screens."""
from ui.display import (heading, section, step, notice, success, warn, show_table, show_summary, pesos, qty_text)
from ui.inputs import (ask, ask_name, ask_optional, ask_date, intask, moneyask,
                       amountask, choose, confirm, action_menu)


def inventory(api, include_archived=False):
    items = api.call("GET", "/api/inventory")
    show_table(
        ["ID", "Chocolate product", "Price", "Stock", "Booth", "Reserved", "Available"],
        [(p["id"], p["name"], pesos(p["price"]), p["stock"], p["allocated"],
          p["reserved"], p["available"]) for p in items],
        "PRODUCT INVENTORY",
    )
    if include_archived:
        archived = [p for p in api.call("GET", "/api/products") if not p["active"]]
        if archived:
            show_table(["ID", "Archived product"],
                       [(p["id"], p["name"]) for p in archived], "ARCHIVED PRODUCTS")
    return items



def select_products(api, title, check_stock=False):
    heading(title, "Enter a product ID, or 0 when finished.")
    products = inventory(api)
    allowed = {p["id"] for p in products}
    chosen = []
    while True:
        pid = intask("Product ID (0 = done)", 0, minimum=0, allowed=allowed | {0})
        if pid == 0:
            break
        if any(item["product_id"] == pid for item in chosen):
            warn("You already added that product. Choose another product.")
            continue
        product = next(p for p in products if p["id"] == pid)
        maximum = product["available"] if check_stock else 1_000_000_000
        if maximum == 0:
            warn("This product has no available stock.")
            continue
        quantity = intask("Quantity", maximum=maximum)
        chosen.append({"product_id": pid, "quantity": quantity})
        success(f"Added {quantity} of {product['name']}.")
    if chosen:
        names = {p["id"]: p["name"] for p in products}
        show_table(["Product", "Quantity"],
                   [(names[x["product_id"]], x["quantity"]) for x in chosen], "YOUR SELECTION")
    return chosen



def show_ingredients(api):
    items = api.call("GET", "/api/ingredients")
    show_table(["ID", "Ingredient", "Stock", "Unit", "Stock value", "Avg cost/unit"],
               [(x["id"], x["name"], qty_text(x["quantity"]), x["unit"],
                 pesos(x["stock_value"]), f"₱{x['average_unit_cost']:.4f}")
                for x in items], "INGREDIENT INVENTORY")
    return items



def ingredients_menu(api):
    heading("Ingredient inventory and purchases",
            "Ingredients can be shared by many chocolate recipes.")
    items = show_ingredients(api)
    action = action_menu([
        ("add", "Register a new ingredient"),
        ("purchase", "Record new ingredient purchase"),
        ("rename", "Rename an ingredient"),
        ("archive", "Archive empty, unused ingredient"),
        ("history", "View ingredient purchase history"),
    ])
    if action == "add":
        step(1, "New ingredient information", "Register this once; it can be used in many recipes.")
        name = ask_name("Ingredient name")
        unit = choose("Measurement unit", ["g", "pcs"], "g")
        if confirm("Add ingredient to catalog?"):
            row = api.call("POST", "/api/ingredients", {"name": name, "unit": unit})
            success(f"Ingredient #{row['id']} created. You can now record a purchase.")
    elif action == "purchase":
        if not items:
            warn("Register an ingredient first.")
            return
        step(1, "Choose ingredient")
        show_ingredients(api)
        iid = intask("Ingredient ID", allowed={x["id"] for x in items})
        item = next(x for x in items if x["id"] == iid)
        step(2, "Purchase details", "Enter quantity bought and the total amount paid.",
             new_page=True, context=f"Purchasing: {item['name']}")
        notice(f"Buying more {item['name']} ({item['unit']}).")
        if item["unit"] == "g":
            unit = choose("Purchase quantity measured in", ["g", "kg"], "g")
            entered = amountask("Purchased weight (" + unit + ")", "g")
            quantity = entered * 1000 if unit == "kg" else entered
        else:
            quantity = amountask("Purchased pieces", "pcs")
        cost = moneyask("Total amount PAID for this purchase (₱)", allow_zero=False)
        day = ask_date("Purchase date")
        note = ask_optional("Supplier / note (optional)", 300)
        step(3, "Review purchase", "Confirm the amount before adding it to inventory.",
             new_page=True, context="Ingredient purchase")
        show_summary("Review purchase", [("Ingredient", item["name"]),
                                          ("Quantity to ADD", f"{qty_text(quantity)} {item['unit']}"),
                                          ("Purchase cost", pesos(cost))])
        if confirm("Save purchase and add to ingredient stock?"):
            row = api.call("POST", "/api/purchases", {
                "ingredient_id": iid, "quantity": quantity, "total_cost": cost,
                "date": day, "note": note})
            success(f"Purchase #{row['id']} saved. Stock increased by {qty_text(quantity)} {item['unit']}.")
    elif action == "rename":
        if not items:
            warn("No ingredients to rename.")
            return
        show_ingredients(api)
        iid = intask("Ingredient ID", allowed={x["id"] for x in items})
        name = ask_name("New ingredient name")
        if confirm("Save ingredient name?"):
            api.call("PUT", f"/api/ingredients/{iid}", {"name": name})
            success("Ingredient updated. Existing recipes still refer to this ingredient ID.")
    elif action == "archive":
        if not items:
            return
        show_ingredients(api)
        iid = intask("Ingredient ID", allowed={x["id"] for x in items})
        warn("Only ingredients with no stock and no active recipe links can be archived.")
        if confirm("Archive ingredient?", default=False):
            api.call("DELETE", f"/api/ingredients/{iid}")
            success("Ingredient archived.")
    elif action == "history":
        purchases = api.call("GET", "/api/purchases")
        names = {x["id"]: x["name"] for x in items}
        show_table(["ID", "Date", "Ingredient", "Quantity", "Total paid"],
                   [(x["id"], x["date"], names.get(x["ingredient_id"], x["ingredient_id"]),
                     f"{qty_text(x['quantity'])} {x['unit']}", pesos(x["total_cost"]))
                    for x in purchases], "PURCHASE HISTORY")



def recipe_menu(api, product_id=None):
    heading("Product recipes", "Recipes are a reference. Production records actual ingredients used.")
    products = inventory(api)
    if not products:
        warn("No active products available.")
        return
    if product_id is None:
        product_id = intask("Product ID to view or edit recipe", allowed={p["id"] for p in products})
    product = api.call("GET", f"/api/products/{product_id}")
    ingredients = show_ingredients(api)
    by_id = {x["id"]: x for x in ingredients}
    show_table(["Ingredient", "Suggested amount per pouch/bar"],
               [(by_id.get(x["ingredient_id"], {}).get("name", "Unknown ingredient"),
                 f"{qty_text(x['quantity'])} {by_id.get(x['ingredient_id'], {}).get('unit', '')}")
                for x in product.get("recipe", [])], f"RECIPE: {product['name']}")
    if not ingredients:
        warn("Register the ingredients first in menu 2.")
        return
    if not confirm("Create or replace this product's recipe?", default=not bool(product["recipe"])):
        return
    step(1, "Add ingredients to recipe", "Suggested quantities are per finished pouch or bar.")
    show_ingredients(api)
    notice("Choose each ingredient. Suggested amounts are for ONE pouch/bar only.")
    notice("Type 0 when done. Setting a recipe replaces its previous ingredient list.")
    recipe = []
    available_ids = {x["id"] for x in ingredients}
    while True:
        iid = intask("Ingredient ID (0 = finish recipe)", 0, minimum=0, allowed=available_ids | {0})
        if iid == 0:
            break
        if any(row["ingredient_id"] == iid for row in recipe):
            warn("This ingredient is already included.")
            continue
        item = by_id[iid]
        quantity = amountask(f"Suggested {item['name']} per pouch/bar ({item['unit']})", item["unit"])
        recipe.append({"ingredient_id": iid, "quantity": quantity})
    if not recipe:
        warn("No ingredients selected; previous recipe was not changed.")
        return
    step(2, "Review recipe", "The recipe is a guide; actual production uses measured quantities.",
         new_page=True, context="Recipe confirmation")
    show_table(["Ingredient", "Per finished unit"],
               [(by_id[x["ingredient_id"]]["name"],
                 f"{qty_text(x['quantity'])} {by_id[x['ingredient_id']]['unit']}") for x in recipe],
               "RECIPE PREVIEW")
    if confirm("Save this recipe?"):
        api.call("PUT", f"/api/products/{product_id}/recipe", {"items": recipe})
        success("Recipe saved. You can record actual ingredient use during production.")



def products_menu(api):
    heading("Product management", "Add chocolates and connect them to ingredient recipes.")
    products = inventory(api, include_archived=True)
    action = action_menu([
        ("add", "Add product and set its recipe"),
        ("edit", "Edit product name or price"),
        ("recipe", "View or edit product recipe"),
        ("archive", "Archive product (keeps sales history)"),
    ])
    if action == "add":
        step(1, "New product details")
        name = ask_name("Product name")
        price = moneyask("Selling price (₱)", allow_zero=False)
        if confirm("Save new product?"):
            result = api.call("POST", "/api/products", {"name": name, "price": price})
            success(f"Product #{result['id']} created: {result['name']}")
            step(2, "Assign a recipe to your new product")
            recipe_menu(api, result["id"])
    elif action == "edit":
        if not products:
            return
        inventory(api)
        pid = intask("Product ID to edit", allowed={p["id"] for p in products})
        product = api.call("GET", f"/api/products/{pid}")
        while True:
            new_name = ask("Product name", product["name"])
            if new_name.strip() and len(new_name) <= 100:
                break
            warn("Product name must have 1 to 100 nonblank characters.")
        price = moneyask("New selling price (₱)", product["price"], allow_zero=False)
        if confirm("Save changes?"):
            updated = api.call("PUT", f"/api/products/{pid}", {"name": new_name, "price": price})
            success(f"Updated product #{pid}: {updated['name']}")
    elif action == "recipe":
        recipe_menu(api)
    elif action == "archive":
        if not products:
            return
        inventory(api)
        pid = intask("Active product ID to archive", allowed={p["id"] for p in products})
        warn("Archiving hides this product from future transactions, but preserves its history.")
        if confirm("Archive this product?", default=False):
            api.call("DELETE", f"/api/products/{pid}")
            success(f"Product #{pid} archived.")

