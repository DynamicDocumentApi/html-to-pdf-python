"""Loads invoice.json and adds the line amounts and totals the template prints.

Money is calculated with Decimal and rounded to cents, then passed to the template as numbers.
"""

import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

CENT = Decimal("0.01")
HERE = Path(__file__).parent


def money(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"  # November 2, 2026


def load_invoice(path: Path = HERE / "invoice.json") -> dict:
    invoice = json.loads(path.read_text(encoding="utf-8"))
    invoice["issued"] = long_date(invoice["issued"])
    invoice["due"] = long_date(invoice["due"])

    subtotal = Decimal("0")
    for item in invoice["items"]:
        amount = Decimal(item["unit_price"]) * item["qty"]
        subtotal += amount
        item["unit_price"] = money(Decimal(item["unit_price"]))
        item["amount"] = money(amount)

    tax_rate = Decimal(invoice["tax_rate"])
    shipping = Decimal(invoice["shipping"])
    tax = (subtotal * tax_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    invoice["totals"] = {
        "subtotal": money(subtotal),
        "tax_percent": float(tax_rate * 100),
        "tax": money(tax),
        "shipping": money(shipping),
        "total": money(subtotal + tax + shipping),
    }
    return invoice
