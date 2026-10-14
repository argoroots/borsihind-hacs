"""Price calculations for Börsihind.ee, shared logic with the web and TRMNL clients.

Pure functions without Home Assistant imports, so they can be tested on their own.
"""
from __future__ import annotations

from datetime import datetime, tzinfo
import math
from typing import Any

# Cheapest window lengths in hours
CHEAPEST_HOURS = (1, 2, 3, 4)


def js_round(value: float) -> int:
    """Round halves up like JavaScript Math.round (Python round() rounds halves to even)."""
    return math.floor(value + 0.5)


def parse_time(value: str) -> datetime:
    """Parse a UTC timestamp like 2026-10-14T06:30:00Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def process_prices(
    raw: dict[str, Any], now: datetime, marginal: float, time_zone: tzinfo
) -> list[dict[str, Any]]:
    """Convert price data to slots from the current one onwards.

    Prices in the file are EUR/kWh with VAT. Returned components are in cents/kWh.
    `marginal` is in cents/kWh and already includes VAT. `time_zone` is used for
    the HH:MM `time` labels (the Home Assistant time zone).
    """
    prices = []

    for item in raw.get("prices", []):
        start = parse_time(item["start"])
        end = parse_time(item["end"])

        # Keep the current slot and everything after it
        if end <= now:
            continue

        prices.append({
            "start": start,
            "end": end,
            "time": start.astimezone(time_zone).strftime("%H:%M"),
            "electricity": item["electricity"] * 100,
            "transmission": item["transmission"] * 100,
            "renewable": item["renewable"] * 100,
            "excise": item["excise"] * 100,
            "supply_security": item["supplySecurity"] * 100,
            "total": item["total"] * 100 + marginal,
        })

    return prices


def find_cheapest(prices: list[dict[str, Any]], span: int) -> dict[str, Any] | None:
    """Find the cheapest window of `span` consecutive slots.

    Same algorithm as the web and TRMNL: the current slot is included, sums are
    compared at 0.01 cent precision and the earliest window wins a tie.
    Returns None when there is not enough data.
    """
    if span <= 0 or len(prices) < span:
        return None

    lowest_sum = float("inf")
    lowest_index = -1

    for i in range(len(prices) - span + 1):
        window_sum = sum(p["total"] for p in prices[i:i + span])

        if lowest_index < 0 or js_round(window_sum * 100) < js_round(lowest_sum * 100):
            lowest_sum = window_sum
            lowest_index = i

    return {
        "start": prices[lowest_index]["start"],
        "end": prices[lowest_index + span - 1]["end"],
        "average": lowest_sum / span,
    }


def summarize(prices: list[dict[str, Any]], slots_per_hour: int) -> dict[str, Any]:
    """Current price, statistics and cheapest windows for the processed slots."""
    totals = [p["total"] for p in prices]

    return {
        "current": prices[0],
        "prices": prices,
        "average": sum(totals) / len(totals),
        "min": min(totals),
        "max": max(totals),
        "cheapest": {
            hours: find_cheapest(prices, hours * slots_per_hour)
            for hours in CHEAPEST_HOURS
        },
    }
