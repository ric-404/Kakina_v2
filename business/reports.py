"""Daily and all-time revenue, ingredient costs and selling reports."""

from core import get, valid_date


def reports(state, date=None):
    """Report recorded revenue and costs, NOT a true net-profit calculation."""
    if date:
        date = valid_date(date)

    sales = [row for row in state["sales"] if not date or row["date"] == date]
    production = [row for row in state["production"] if not date or row["date"] == date]

    product_revenue = round(sum(row["subtotal"] for row in sales), 2)
    fees = round(sum(row["delivery_fee"] for row in sales), 2)
    revenue = round(product_revenue + fees, 2)
    costs = round(sum(row["total_cost"] for row in production), 2)

    quantities = {}
    by_channel = {}
    by_booth = {}
    by_payment = {}
    by_date = {}

    for row in sales:
        name = row["product_name"]
        quantities[name] = quantities.get(name, 0) + row["quantity"]

        channel = row["channel"]
        by_channel[channel] = round(by_channel.get(channel, 0) + row["total"], 2)

        method = row["payment"]
        by_payment[method] = round(by_payment.get(method, 0) + row["total"], 2)

        day = row["date"]
        by_date[day] = round(by_date.get(day, 0) + row["total"], 2)

        if row["event_id"] is not None:
            event = get(state, "events", row["event_id"])
            by_booth[event["name"]] = round(
                by_booth.get(event["name"], 0) + row["total"], 2
            )

    return {
        "filter_date": date,
        "sales_revenue": revenue,
        "product_revenue": product_revenue,
        "delivery_fees": fees,
        "recorded_production_expenses": costs,
        "revenue_less_recorded_expenses_not_profit": round(revenue - costs, 2),
        "product_quantities_sold": quantities,
        "revenue_by_channel": by_channel,
        "revenue_by_booth": by_booth,
        "revenue_by_payment": by_payment,
        "revenue_by_date": by_date,
        "sales_count": len(sales),
        "production_count": len(production),
        "ingredient_purchase_expenses": round(sum(x["total_cost"] for x in state["purchases"]
                if not date or x["date"] == date), 2),
    }

