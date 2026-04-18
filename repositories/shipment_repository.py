from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


class ShipmentRepositoryError(RuntimeError):
    """Base error for shipment repository operations."""


class DuplicateTrackingNumberError(ShipmentRepositoryError):
    """Raised when a tracking number already exists."""


class ShipmentNotFoundError(ShipmentRepositoryError):
    """Raised when a shipment does not exist."""


class ShipmentSchemaCompatibilityError(ShipmentRepositoryError):
    """Raised when the shipments table schema is incompatible with the app."""

    def __init__(self, *, detail: str, remediation_sql: str) -> None:
        self.detail = detail
        self.remediation_sql = remediation_sql
        self.summary_message = (
            "La tabla shipments no tiene la columna estimated_delivery_date. "
            "Aplica el SQL de compatibilidad y vuelve a intentar."
        )
        super().__init__(f"{self.summary_message}\n{remediation_sql}")


@dataclass(frozen=True)
class ShipmentMutation:
    destination_city: str
    estimated_delivery_date: date | None
    origin_city: str
    status: str
    tracking_number: str


@dataclass(frozen=True)
class ShipmentRecord:
    created_at: datetime | None
    destination_city: str
    estimated_delivery_date: date | None
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

    def update_shipment(self, shipment_id: int, payload: ShipmentMutation) -> ShipmentRecord:
        ...

    def delete_shipment(self, shipment_id: int) -> None:
        ...