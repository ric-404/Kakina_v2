"""Shared JSON storage and validation for the Kakina program.

Business operations live in business/. API endpoints live in api.py.
Only this module reads or writes the JSON file.
"""

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import date as CalendarDate
from decimal import Decimal, InvalidOperation
from pathlib import Path

try:
    import fcntl  # Available on Linux (including Arch/CachyOS).
except ImportError:
    fcntl = None


DATA_PATH = Path(
    os.environ.get("KAKINA_DATA", Path(__file__).with_name("kakina_data.json"))
)

SEED_PRODUCTS = [
    {"name": "Purong Cacao (Tablea) Pouch 100g (11 pcs)", "price": 120},
    {"name": "60% Dark Chocolate with Pistachio Nuts Pouch 20g", "price": 40},
    {"name": "60% Dark Chocolate with Pistachio Nuts Bar 60g", "price": 150},
    {"name": "60% Dark Chocolate with Mango Bits Pouch 20g", "price": 40},
    {"name": "60% Dark Chocolate with Mango Bits Bar 60g", "price": 150},
]


class RuleError(ValueError):
    """An invalid business operation, such as selling unavailable stock."""




def new_state():
    """Starting data. Products have no stock until production is recorded."""
    products = []
    for number, item in enumerate(SEED_PRODUCTS, start=1):
        products.append({
            "id": number,
            "name": item["name"],
            "price": item["price"],
            "stock": 0,
            "active": True, "recipe": [],
        })

    return {
        "next_id": 6,
        "products": products,
        "production": [],
        "ingredients": [],
        "purchases": [],
        "events": [],
        "reservations": [],
        "sales": [],
        "adjustments": [],
    }



@contextmanager
def locked_state(save=False):
    """Read the JSON file and save it only after a successful operation.

    A temporary file avoids partly-written JSON. A simple file lock helps
    prevent two requests from saving changes over each other on Linux.
    """
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = str(DATA_PATH) + ".lock"

    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        if fcntl:
            lock_type = fcntl.LOCK_EX if save else fcntl.LOCK_SH
            fcntl.flock(lock_file.fileno(), lock_type)

        try:
            if DATA_PATH.exists():
                with open(DATA_PATH, "r", encoding="utf-8") as file:
                    try:
                        state = json.load(file)
                    except json.JSONDecodeError as exc:
                        raise RuleError(
                            "JSON data file is damaged. Restore your backup; "
                            "do not delete the file."
                        ) from exc
            else:
                state = new_state()

            # Open JSON files created by earlier versions without losing records.
            state.setdefault("ingredients", [])
            state.setdefault("purchases", [])
            for product in state.get("products", []):
                product.setdefault("recipe", [])
            yield state

            if save:
                descriptor, temporary_path = tempfile.mkstemp(
                    dir=DATA_PATH.parent, prefix="kakina_", suffix=".tmp"
                )
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                        json.dump(state, file, indent=2, ensure_ascii=False)
                        file.flush()
                        os.fsync(file.fileno())
                    os.replace(temporary_path, DATA_PATH)
                finally:
                    if os.path.exists(temporary_path):
                        os.remove(temporary_path)
        finally:
            if fcntl:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)



def read():
    with locked_state() as state:
        return state



def execute(function, *args, **kwargs):
    """Run one change and save the resulting JSON data."""
    with locked_state(save=True) as state:
        return function(state, *args, **kwargs)



def get(state, collection, record_id):
    for record in state[collection]:
        if record["id"] == record_id:
            return record
    raise RuleError(f"{collection} record not found: {record_id}")



def next_id(state):
    number = state["next_id"]
    state["next_id"] += 1
    return number



def whole_number(value, label="Quantity", allow_zero=False):
    """Accept only whole numbers; do not accept booleans or decimal text."""
    if isinstance(value, bool):
        raise RuleError(f"{label} must be a whole number.")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.strip().isdigit() and len(value.strip()) <= 12:
        number = int(value.strip())
    else:
        raise RuleError(f"{label} must be a whole number (example: 5).")

    minimum = 0 if allow_zero else 1
    if number < minimum:
        raise RuleError(f"{label} must be at least {minimum}.")
    if number > 1_000_000_000:
        raise RuleError(f"{label} is too large.")
    return number



def peso(value, label="Amount", allow_zero=True):
    """Validate peso amounts, rejecting NaN, infinity and > 2 decimals."""
    if isinstance(value, bool) or value is None:
        raise RuleError(f"{label} must be a valid peso amount.")
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise RuleError(f"{label} must be a valid peso amount.") from None

    if not amount.is_finite():
        raise RuleError(f"{label} must be a finite number.")
    if amount < 0 or (not allow_zero and amount == 0):
        raise RuleError(f"{label} must be {'positive' if not allow_zero else 'non-negative'}.")
    if amount >= 10_000_000_000:
        raise RuleError(f"{label} is too large.")
    if amount != amount.quantize(Decimal("0.01")):
        raise RuleError(f"{label} can have at most two decimal places.")
    return float(amount)



def text_value(value, label, max_length=100):
    if not isinstance(value, str) or not value.strip():
        raise RuleError(f"{label} cannot be empty.")
    result = value.strip()
    if not all(char.isprintable() for char in result):
        raise RuleError(f"{label} cannot contain control characters.")
    if len(result) > max_length:
        raise RuleError(f"{label} must be {max_length} characters or fewer.")
    return result



def optional_text(value, label="Notes", max_length=300):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise RuleError(f"{label} must be text.")
    if not all(char.isprintable() for char in value.strip()):
        raise RuleError(f"{label} cannot contain control characters.")
    if len(value.strip()) > max_length:
        raise RuleError(f"{label} must be {max_length} characters or fewer.")
    return value.strip()



def valid_date(value):
    text = text_value(value, "Date")
    try:
        parsed = CalendarDate.fromisoformat(text)
    except ValueError:
        raise RuleError("Date must be a real date in YYYY-MM-DD format.") from None
    if parsed.isoformat() != text:
        raise RuleError("Date must use YYYY-MM-DD (example: 2026-11-02).")
    return text



def valid_choice(value, choices, label):
    text = text_value(value, label).lower()
    if text not in choices:
        raise RuleError(f"{label} must be: {', '.join(choices)}.")
    return text



def active_product(state, product_id):
    product = get(state, "products", product_id)
    if not product["active"]:
        raise RuleError("This product is archived and cannot be used.")
    return product



def decimal_amount(value, label, allow_zero=False, places=3):
    """Accept a nonnegative quantity, without scientific notation or NaN."""
    if isinstance(value, bool) or value is None:
        raise RuleError(f"{label} must be a valid number.")
    raw = str(value).strip()
    if not raw or len(raw) > 20 or "e" in raw.lower():
        raise RuleError(f"{label} must be a valid number.")
    try:
        number = Decimal(raw)
    except InvalidOperation:
        raise RuleError(f"{label} must be a valid number.") from None
    if not number.is_finite() or number < 0 or (not allow_zero and number == 0):
        raise RuleError(f"{label} must be positive.")
    if number > 1_000_000_000 or number != number.quantize(Decimal(10) ** -places):
        raise RuleError(f"{label} is too large or has too many decimal places (max {places}).")
    return number



def as_decimal(value):
    return Decimal(str(value))


