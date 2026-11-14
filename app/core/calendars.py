"""Bank-business-day arithmetic from pinned holiday rules, never demo dates."""

from datetime import date, timedelta

import holidays


def is_business_day(day: date, rail: str) -> bool:
    if day.weekday() >= 5:
        return False
    if rail == "SEPA":
        calendar = holidays.financial_holidays("ECB", years=day.year)
    elif rail == "FPS":
        calendar = holidays.country_holidays("GB", subdiv="ENG", years=day.year)
    elif rail in {"ACH", "SWIFT"}:
        calendar = holidays.country_holidays("US", years=day.year)
    else:
        raise ValueError("Unsupported payment rail")
    return day not in calendar


def move_business_days(day: date, days: int, rail: str) -> date:
    direction = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining:
        day += timedelta(days=direction)
        if is_business_day(day, rail):
            remaining -= 1
    return day
