from datetime import datetime, date, time
from typing import Optional
from sqlmodel import SQLModel, Field


class Resource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(default="mrwolf-pizzeria", index=True)
    name: str
    resource_type: str = "table"
    capacity: int = 1


class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(default="mrwolf-pizzeria", index=True)
    name: str
    duration_min: int = 90
    requires_resource_type: str = "table"


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(default="mrwolf-pizzeria", index=True)
    resource_id: Optional[int] = Field(default=None, foreign_key="resource.id")
    service_id: Optional[int] = Field(default=None, foreign_key="service.id")
    customer_name: str
    phone: Optional[str] = None
    booking_date: date
    booking_time: time
    party_size: Optional[int] = None
    status: str = "confirmed"  # confirmed | cancelled | completed
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CallLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(default="mrwolf-pizzeria", index=True)
    booking_id: Optional[int] = Field(default=None, foreign_key="booking.id")
    transcript: Optional[str] = None
    outcome: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
