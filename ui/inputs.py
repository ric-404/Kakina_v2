"""Validated keyboard input shared by all menus.

Each function keeps asking until the answer is valid.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from ui.display import warn, border, heading

def ask(label, default=None):
    """Ask for text. Pressing Enter chooses the provided default."""
    display = f" [{default}]" if default is not None and str(default) else ""
    value = input(f"  {label}{display}: ").strip()
    if not value and default is not None:
        return str(default).strip()
    return value


def ask_name(label, max_length=100):
    while True:
        value = ask(label).strip()
        if not value:
            warn("This field cannot be blank.")
        elif len(value) > max_length:
            warn(f"Use at most {max_length} characters.")
        else:
            return value


def ask_optional(label, max_length=100):
    while True:
        value = ask(label)
        if len(value) <= max_length:
            return value
        warn(f"Use at most {max_length} characters.")


def ask_date(label, blank_allowed=False):
    default = "" if blank_allowed else date.today().isoformat()
    while True:
        value = ask(label, default)
        if blank_allowed and not value:
            return ""
        try:
            if date.fromisoformat(value).isoformat() == value:
                return value
        except ValueError:
            pass
        warn("Enter a real date as YYYY-MM-DD (example: 2026-11-02).")


def intask(label, default=None, minimum=1, maximum=1_000_000_000, allowed=None):
    """Ask for an integer. Never accepts letters, negative numbers or 2.5."""
    while True:
        value = ask(label, default)
        if value.isdigit() and len(value) <= 12:
            number = int(value)
            if minimum <= number <= maximum and (allowed is None or number in allowed):
                return number
        if allowed is not None:
            warn("Choose a number or ID shown on this screen.")
        else:
            warn(f"Enter a whole number from {minimum} to {maximum}.")


def moneyask(label, default=0, allow_zero=True):
    """Accept only non-negative peso amounts with at most two decimals."""
    while True:
        value = ask(label, default)
        try:
            amount = Decimal(value)
            if (amount.is_finite() and 0 <= amount < 10_000_000_000
                    and (allow_zero or amount > 0)
                    and amount == amount.quantize(Decimal("0.01"))):
                return float(amount)
        except (InvalidOperation, ValueError):
            pass
        warn("Enter a valid amount, such as 120 or 120.50 (not negative).")


def amountask(label, unit="g", default=None, maximum=None):
    """Ask for an ingredient weight (g) or whole package/item count (pcs)."""
    while True:
        value = ask(label, default)
        try:
            if not value or "e" in value.lower() or len(value) > 20:
                raise ValueError
            number = Decimal(value)
            places = 3 if unit == "g" else 0
            if (not number.is_finite() or number <= 0 or number > 1_000_000_000
                    or number != number.quantize(Decimal(10) ** -places)):
                raise ValueError
            if maximum is not None and number > Decimal(str(maximum)):
                warn(f"Not enough stock. Only {maximum} {unit} remains.")
                continue
            return float(number) if unit == "g" else int(number)
        except (InvalidOperation, ValueError):
            warn("Enter a positive quantity" +
                 (" (up to 3 decimals)." if unit == "g" else " (whole pieces only)."))


def choose(label, options, default=None):
    """Display numbered choices. Accepts a number or the actual option name."""
    options = list(options)
    print()
    for number, option in enumerate(options, 1):
        print(f"  {number}. {option.title()}")
    while True:
        answer = ask(label + " (number or name)", default or options[0]).lower()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        if answer in options:
            return answer
        warn("Choose one of the options displayed above.")


def confirm(message, default=True):
    while True:
        answer = ask(message + " (y/n)", "y" if default else "n").lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        warn("Please enter y for Yes or n for No.")


def action_menu(options):
    """Bordered submenu shared by product, booth and reservation screens."""
    menu_options = [f"[{number}] {label}" for number, (_, label) in enumerate(options, 1)]
    menu_options.append("[0] Back")
    border("ACTIONS", menu_options)
    picked = intask("Choose an action", 0, minimum=0, maximum=len(options))
    if picked == 0:
        return None
    action, label = options[picked - 1]
    heading(label, "KAKINA | SELECTED ACTION")
    return action

