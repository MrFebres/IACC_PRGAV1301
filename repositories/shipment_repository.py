from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ShipmentMutation:
    destination_city: str
    origin_city: str
    status: str
    tracking_number: str


@dataclass(frozen=True)
class ShipmentRecord:
    created_at: datetime | None
    destination_city: str
    id: int
    origin_city: str
    status: str
    tracking_number: str
    updated_at: datetime | None


@dataclass(frozen=True)
class ShipmentSummary:
    shipment_count: int
    status: str


class ShipmentRepository(Protocol):
    def create_shipment(self, payload: ShipmentMutation) -> ShipmentRecord:
        ...

    def list_shipments(self) -> tuple[ShipmentRecord, ...]:
        ...

    def summarize_shipments(self) -> tuple[ShipmentSummary, ...]:
        ...

    def update_shipment_status(self, shipment_id: int, status: str) -> ShipmentRecord:
        ...