"""Typed fixture and tool-response records used by the demo boundary."""
from __future__ import annotations

from typing import Literal, TypedDict


class Hotel(TypedDict):
    hotel_id: str
    name: str
    assigned_specialist_id: str
    monthly_budget_cap_jpy: int


class Campaign(TypedDict):
    campaign_id: str
    hotel_id: str
    monthly_budget_jpy: int
    spend_30d_jpy: int


class Booking(TypedDict):
    booking_id: str
    hotel_id: str
    campaign_id: str
    gross_value_jpy: int
    status: Literal["retained", "cancelled"]


class DataQuality(TypedDict):
    attribution: str
    coverage: float
    contains_pii: bool
