"""Chocolate production: measured ingredient use and finished product count."""
from ui.display import heading, section, step, notice, success, warn, show_table, show_summary, qty_text, pesos
from ui.inputs import ask_date, intask, amountask, ask_optional, confirm
from ui.catalog import inventory, show_ingredients


def production_menu(api):
    heading("Make chocolate products", "Weigh real ingredients first; count finished units after molding.")
    step(1, "Select product and date")
    day = ask_date("Production date (YYYY-MM-DD)")
    products = inventory(api)
    if not products:
        warn("Add a chocolate product first.")
        return
    pid = intask("Product ID to produce", allowed={x["id"] for x in products})
    product = api.call("GET", f"/api/products/{pid}")
    recipe = product.get("recipe", [])
    if not recipe:
        warn("This product has no recipe. Set its recipe in menu 3 before production.")
        return
    ingredients = {x["id"]: x for x in show_ingredients(api)}
    show_table(["Ingredient", "Recipe amount / item", "Currently in stock"],
               [(ingredients[x["ingredient_id"]]["name"],
                 f"{qty_text(x['quantity'])} {ingredients[x['ingredient_id']]['unit']}",
                 f"{qty_text(ingredients[x['ingredient_id']]['quantity'])} {ingredients[x['ingredient_id']]['unit']}")
                for x in recipe], "PRODUCT RECIPE")
    step(2, "Enter actual ingredient usage", "The saved recipe is a guide only. Enter the amount weighed for this run.")
    actual = []
    for row in recipe:
        item = ingredients[row["ingredient_id"]]
        if item["quantity"] <= 0:
            warn(f"No {item['name']} left in stock. Purchase ingredients first.")
            return
        section(f"INGREDIENT: {item['name']}", f"Available: {qty_text(item['quantity'])} {item['unit']}")
        quantity = amountask(f"Actual {item['name']} used ({item['unit']})", item["unit"],
                             maximum=item["quantity"])
        actual.append({"ingredient_id": item["id"], "quantity": quantity})
    step(3, "Count molded and packaged chocolates", new_page=True,
         context=f"Production: {product['name']}")
    finished = intask("Actual finished pouches/bars counted")
    notes = ask_optional("Production notes (optional)", 300)
    step(4, "Review before saving", "Nothing is deducted until you confirm.",
         new_page=True, context="Production confirmation")
    show_summary("Review production run", [
        ("Product", product["name"]),
        ("Production date", day),
        ("Finished products COUNTED", finished),
    ])
    show_table(["Ingredient", "Actual quantity used"],
               [(ingredients[x["ingredient_id"]]["name"],
                 f"{qty_text(x['quantity'])} {ingredients[x['ingredient_id']]['unit']}") for x in actual],
               "STOCK TO BE CONSUMED")
    if confirm("Deduct ingredients and add finished products to inventory?"):
        row = api.call("POST", "/api/production", {
            "date": day, "product_id": pid, "ingredients_used": actual,
            "finished_quantity": finished, "note": notes})
        success(f"Production #{row['id']} saved. {finished} finished units added.")
        notice(f"Weighted-average ingredient cost used: {pesos(row['total_cost'])}.")

