"""Terminal layout for the Kakina CLI. Uses only standard Python."""
import os
import shutil
import sys


def clear_screen():
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def screen_width():
    return max(60, min(shutil.get_terminal_size((90, 24)).columns, 110))


def divider():
    print("  " + "-" * (screen_width() - 2))


def border(title, rows=None, symbol="-"):
    """Print a simple ASCII box containing a heading and optional menu rows."""
    width = screen_width() - 6
    edge = "  +" + symbol * width + "+"
    print(edge)
    print("  | " + str(title).upper()[:width - 2].ljust(width - 2) + " |")
    print(edge)
    if rows:
        for row in rows:
            print("  | " + str(row)[:width - 2].ljust(width - 2) + " |")
        print(edge)
    print()


def heading(title, subtitle=""):
    clear_screen()
    border(title, [subtitle] if subtitle else None, "=")


def section(title, description=""):
    border(title, [description] if description else None)


def step(number, title, description="", new_page=False, context=""):
    if new_page:
        clear_screen()
        if context:
            border(context, symbol="=")
    section(f"STEP {number} - {title}", description)


def message(label, text):
    print(f"  [{label}] {text}")


def notice(text):
    message("INFO", text)


def success(text):
    message("SAVED", text)


def warn(text):
    message("NOTICE", text)


def error(text):
    message("ERROR", text)


def qty_text(value):
    return f"{float(value):g}"


def pesos(value):
    amount = float(value)
    return f"-₱{abs(amount):,.2f}" if amount < 0 else f"₱{amount:,.2f}"


def wrap_name(text, width):
    """Split long names into lines that fit a table column."""
    words = str(text).split()
    lines = []
    line = ""
    for word in words:
        while len(word) > width:
            if line:
                lines.append(line)
                line = ""
            lines.append(word[:width])
            word = word[width:]
        if not word:
            continue
        if not line:
            line = word
        elif len(line) + len(word) + 1 <= width:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def shorten(text, width):
    text = str(text)
    if len(text) <= width:
        return text
    return text[:max(0, width - 3)] + "..." if width >= 4 else text[:width]


def show_table(headers, rows, title=""):
    """Show data in a bordered table. Only name columns wrap onto new lines."""
    headers = [str(name) for name in headers]
    rows = [[str(value) for value in row] for row in rows]
    if title:
        print("  " + title.upper())
    if not rows:
        print("  No records found.\n")
        return

    count = len(headers)
    room = screen_width() - 2 - (3 * count + 1)
    name_columns = {i for i, header in enumerate(headers)
                    if any(word in header.lower() for word in ("product", "ingredient", "customer", "location", "name"))}
    widths = []
    minimum = []
    for index, header in enumerate(headers):
        lengths = [len(header)] + [len(row[index]) for row in rows]
        widths.append(min(38 if index in name_columns else 25, max(lengths)))
        minimum.append(min(12 if index in name_columns else 8, max(4, len(header))))

    while sum(widths) > room:
        candidates = [i for i in range(count) if widths[i] > minimum[i]]
        if not candidates:
            break
        largest = max(candidates, key=lambda i: widths[i] - minimum[i])
        widths[largest] -= 1

    if sum(widths) > room:
        for row in rows:
            lines = []
            for header, value in zip(headers, row):
                label = header + ": "
                if any(word in header.lower() for word in
                       ("product", "ingredient", "customer", "location", "name")):
                    pieces = wrap_name(value, max(1, screen_width() - 8 - len(label)))
                    lines.append(label + pieces[0])
                    lines.extend(" " * len(label) + part for part in pieces[1:])
                else:
                    lines.append(label + value)
            border("RECORD", lines)
        return

    line = "  +" + "+".join("-" * (w + 2) for w in widths) + "+"
    print(line)
    print("  | " + " | ".join(shorten(h, w).ljust(w) for h, w in zip(headers, widths)) + " |")
    print(line)

    for row in rows:
        cells = []
        for index, value in enumerate(row):
            if index in name_columns:
                cells.append(wrap_name(value, widths[index]))
            else:
                cells.append([shorten(value, widths[index])])
        for number in range(max(len(cell) for cell in cells)):
            values = [cell[number] if number < len(cell) else "" for cell in cells]
            print("  | " + " | ".join(value.ljust(width) for value, width in zip(values, widths)) + " |")
    print(line + "\n")


def show_summary(title, rows):
    """Display a review box before a transaction is saved."""
    width = screen_width() - 6
    edge = "  +" + "-" * width + "+"
    print(edge)
    print("  | " + shorten(title.upper(), width - 2).ljust(width - 2) + " |")
    print(edge)
    for label, value in rows:
        label = str(label)
        value = str(value)
        prefix = label + ": "
        if any(word in label.lower() for word in ("product", "ingredient", "customer", "name")):
            pieces = wrap_name(value, max(1, width - 2 - len(prefix)))
            for index, piece in enumerate(pieces):
                text = (prefix if index == 0 else " " * len(prefix)) + piece
                print("  | " + text.ljust(width - 2) + " |")
        else:
            print("  | " + shorten(prefix + value, width - 2).ljust(width - 2) + " |")
    print(edge + "\n")
