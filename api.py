"""FastAPI HTTP/JSON interface for Kakina's CLI case-study application.

Run standalone: uvicorn api:app --host 127.0.0.1 --port 8765
The terminal client uses exactly these routes, demonstrating client/server JSON exchange.
"""
from typing import Literal

from fastapi import FastAPI, Response, status
from pydantic import BaseModel, StrictInt, StrictFloat

import core
from business import (ingredients as ingredient_service, inventory as stock,
                      products as product_service, production as production_service,
                      selling as selling_service, reports as report_service)

app = FastAPI(
    title="Kakina Food Products Mfg. REST API",
    description="Local CRUD API for a CLI chocolate production, inventory, reservations, and sales management case study.",
    version="1.0.0",
)


@app.exception_handler(core.RuleError)
async def business_error(request, exc):
    from fastapi.responses import JSONResponse
    message = str(exc)
    message_lower = message.lower()
    conflict_terms = ("stock", "not enough", "already", "archived", "allocated")
    if "not found" in message_lower:
        code = 404
    elif any(term in message_lower for term in conflict_terms):
        code = 409
    else:
        code = 400
    return JSONResponse(status_code=code, content={"detail": message})


class ProductCreate(BaseModel):
    name: str
    price: StrictInt | StrictFloat


class ProductEdit(BaseModel):
    name: str | None = None
    price: StrictInt | StrictFloat | None = None


class IngredientCreate(BaseModel):
    name: str
    unit: Literal["g", "pcs"]


class IngredientEdit(BaseModel):
    name: str


class PurchaseCreate(BaseModel):
    ingredient_id: StrictInt
    quantity: StrictInt | StrictFloat
    total_cost: StrictInt | StrictFloat
    date: str
    note: str = ""


class RecipeItem(BaseModel):
    ingredient_id: StrictInt
    quantity: StrictInt | StrictFloat


class RecipeUpdate(BaseModel):
    items: list[RecipeItem]


class Item(BaseModel):
    product_id: StrictInt
    quantity: StrictInt


class ProductionCreate(BaseModel):
    date: str
    product_id: StrictInt
    ingredients_used: list[RecipeItem]
    finished_quantity: StrictInt
    note: str = ""


class EventCreate(BaseModel):
    name: str
    date: str
    allocations: list[Item]


class EventClose(BaseModel):
    counts: list[Item]


class ReservationCreate(BaseModel):
    customer: str
    product_id: StrictInt
    quantity: StrictInt
    method: Literal["pickup", "delivery"] = "pickup"
    date: str | None = None


class SaleCreate(BaseModel):
    product_id: StrictInt
    quantity: StrictInt
    channel: Literal["direct", "messenger", "booth", "reservation"] = "direct"
    event_id: int | None = None
    reservation_id: int | None = None
    payment: Literal["cash", "gcash"] = "cash"
    delivery_fee: StrictInt | StrictFloat = 0
    customer: str = ""
    date: str | None = None


class AdjustmentCreate(BaseModel):
    product_id: StrictInt
    new_stock: StrictInt
    reason: str


def dump(model: BaseModel):
    return model.model_dump()


@app.get("/api/health")
def health():
    return {"status": "ok", "business": "Kakina Food Products Mfg."}


@app.get("/api/products")
def products():
    return core.read()["products"]


@app.get("/api/products/{product_id}")
def product(product_id: int):
    return core.get(core.read(), "products", product_id)


@app.post("/api/products", status_code=201)
def create_product(data: ProductCreate):
    return core.execute(product_service.product_add, data.name, data.price)


@app.put("/api/products/{product_id}")
def update_product(product_id: int, data: ProductEdit):
    return core.execute(product_service.product_update, product_id, data.name, data.price)


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    core.execute(product_service.product_delete, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/inventory")
def inventory():
    return stock.inventory(core.read())


@app.get("/api/ingredients")
def ingredients():
    return ingredient_service.ingredient_inventory(core.read())


@app.post("/api/ingredients", status_code=201)
def create_ingredient(data: IngredientCreate):
    return core.execute(ingredient_service.ingredient_add, data.name, data.unit)


@app.put("/api/ingredients/{ingredient_id}")
def edit_ingredient(ingredient_id: int, data: IngredientEdit):
    return core.execute(ingredient_service.ingredient_update, ingredient_id, data.name)


@app.delete("/api/ingredients/{ingredient_id}", status_code=204)
def archive_ingredient(ingredient_id: int):
    core.execute(ingredient_service.ingredient_delete, ingredient_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/purchases")
def purchases():
    return core.read()["purchases"]


@app.post("/api/purchases", status_code=201)
def buy_ingredient(data: PurchaseCreate):
    return core.execute(ingredient_service.purchase_add, data.ingredient_id, data.quantity,
                        data.total_cost, data.date, data.note)


@app.put("/api/products/{product_id}/recipe")
def update_recipe(product_id: int, data: RecipeUpdate):
    return core.execute(ingredient_service.recipe_set, product_id, [dump(x) for x in data.items])


@app.get("/api/production")
def production():
    return core.read()["production"]


@app.post("/api/production", status_code=201)
def create_production(data: ProductionCreate):
    return core.execute(production_service.produce, data.date, data.product_id,
                        [dump(x) for x in data.ingredients_used],
                        data.finished_quantity, data.note)


@app.get("/api/events")
def events():
    return core.read()["events"]


@app.post("/api/events", status_code=201)
def create_event(data: EventCreate):
    return core.execute(selling_service.event_open, data.name, data.date, [dump(x) for x in data.allocations])


@app.put("/api/events/{event_id}/close")
def close_event(event_id: int, data: EventClose):
    return core.execute(selling_service.event_close, event_id, [dump(x) for x in data.counts])


@app.get("/api/reservations")
def reservations():
    return core.read()["reservations"]


@app.post("/api/reservations", status_code=201)
def create_reservation(data: ReservationCreate):
    return core.execute(selling_service.reservation_add, data.customer, data.product_id,
                        data.quantity, data.method, data.date)


@app.put("/api/reservations/{reservation_id}/cancel")
def cancel_reservation(reservation_id: int):
    return core.execute(selling_service.reservation_cancel, reservation_id)


@app.get("/api/sales")
def sales():
    return core.read()["sales"]


@app.post("/api/sales", status_code=201)
def create_sale(data: SaleCreate):
    return core.execute(selling_service.sale_add, data.product_id, data.quantity, data.channel,
                        data.event_id, data.reservation_id, data.payment,
                        data.date, data.delivery_fee, data.customer)


@app.post("/api/adjustments", status_code=201)
def adjust_inventory(data: AdjustmentCreate):
    return core.execute(stock.adjust, data.product_id, data.new_stock, data.reason)


@app.get("/api/adjustments")
def adjustments():
    return core.read()["adjustments"]


@app.get("/api/reports")
def reports(date: str | None = None):
    return report_service.reports(core.read(), date)
