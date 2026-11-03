"""Main dashboard, startup, and navigation."""
import argparse
import sys
import threading
import time
import httpx
import uvicorn

from api import app
from ui.client import ApiClient, ApiError, BASE_URL
from ui.display import (heading, border, warn, success, notice, error)
from ui.inputs import intask
from ui.catalog import inventory, ingredients_menu, products_menu
from ui.production import production_menu
from ui.selling import booths_menu, reservations_menu, sales_menu
from ui.reports import reports_menu, adjust_menu


def dashboard(api):
    inventory_rows = api.call("GET", "/api/inventory")
    events = api.call("GET", "/api/events")
    reservations = api.call("GET", "/api/reservations")
    heading("Kakina Food Products Mfg.")
    total = sum(p["stock"] for p in inventory_rows)
    available = sum(p["available"] for p in inventory_rows)
    booths = sum(e["status"] == "open" for e in events)
    reserved_count = sum(r["status"] == "reserved" for r in reservations)
    border("INVENTORY", [f"Stock: {total}  |  Available: {available}  |  Open booths: {booths}  |  Reservations: {reserved_count}"])
    groups = [
        ("INVENTORY & PRODUCTION", [
            ("1", "View finished product inventory"),
            ("2", "Ingredients and purchases (CRUD)"),
            ("3", "Products and recipes (CRUD)"),
            ("4", "Produce chocolates (weigh ingredients, then count)"),
        ]),
        ("ORDERS & SELLING", [
            ("5", "Booth events and unsold stock"),
            ("6", "Customer reservations"),
            ("7", "Record an individual sale"),
        ]),
        ("REPORTS & CONTROL", [
            ("8", "Sales, production and purchase reports"),
            ("9", "Verified inventory adjustment"),
        ]),
    ]
    for group, options in groups:
        border(group, [f"[{key}]  {label}" for key, label in options])
    border("EXIT", ["[0]  Exit program"])



def menu(api):
    """Main menu repeats until the user chooses 0."""
    while True:
        try:
            dashboard(api)
            option = intask("Select menu number", minimum=0, maximum=9)
            if option == 0:
                success("Goodbye!")
                return
            actions = {
                1: lambda: (heading("Product inventory"), inventory(api)),
                2: lambda: ingredients_menu(api),
                3: lambda: products_menu(api),
                4: lambda: production_menu(api),
                5: lambda: booths_menu(api),
                6: lambda: reservations_menu(api),
                7: lambda: sales_menu(api),
                8: lambda: reports_menu(api),
                9: lambda: adjust_menu(api),
            }
            actions[option]()
        except (ApiError, ValueError, httpx.HTTPError) as exc:
            error("Could not finish the action: " + str(exc))
        except (EOFError, KeyboardInterrupt):
            warn("Input cancelled. Returning to the menu.")
            if not sys.stdin.isatty():
                return
        try:
            input("\n  Press Enter to return to main menu...")
        except (EOFError, KeyboardInterrupt):
            return



def start_local_api():
    """Start FastAPI in the background, so a single command launches the CLI."""
    try:
        with httpx.Client(timeout=1) as http:
            response = http.get(BASE_URL + "/api/health")
        if response.status_code == 200 and response.json().get("business") == "Kakina Food Products Mfg.":
            return None, None
        raise ApiError("Port 8765 is already being used by another program.")
    except httpx.RequestError:
        pass
    config = uvicorn.Config(app, host="127.0.0.1", port=8765,
                            log_level="error", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            return server, thread
        if not thread.is_alive():
            break
        time.sleep(0.05)
    raise ApiError("Could not start FastAPI on port 8765. Is another app using that port?")



def main():
    parser = argparse.ArgumentParser(description="Kakina CLI + FastAPI + JSON")
    parser.add_argument("--connect", action="store_true", help="Use an API server already running")
    args = parser.parse_args()
    server = thread = None
    try:
        if not args.connect:
            server, thread = start_local_api()
        with httpx.Client(timeout=3) as http:
            http.get(BASE_URL + "/api/health").raise_for_status()
        notice("Local API ready. API documentation: http://127.0.0.1:8765/docs")
        client = ApiClient()
        try:
            menu(client)
        finally:
            client.http.close()
    except (ApiError, httpx.HTTPError) as exc:
        error("Startup failed: " + str(exc))
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        notice("Exiting the program.")
    finally:
        if server:
            server.should_exit = True
            thread.join(timeout=3)

