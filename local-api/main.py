from datetime import date, time, datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from pydantic import BaseModel

from db import init_db, get_session
from models import Resource, Service, Booking, CallLog

app = FastAPI(title="Mr. Wolf Booking API")
app.mount("/panel", StaticFiles(directory="static", html=True), name="panel")


@app.on_event("startup")
def on_startup():
    init_db()
    seed_defaults()


def seed_defaults():
    """Crea datos de ejemplo si la BD está vacía (mesas + servicio de cena)."""
    from db import engine
    with Session(engine) as session:
        if session.exec(select(Resource)).first():
            return
        tables = [Resource(name=f"Mesa {i}", resource_type="table", capacity=4) for i in range(1, 9)]
        for t in tables:
            session.add(t)
        session.add(Service(name="Cena", duration_min=90, requires_resource_type="table"))
        session.commit()


# ---------- Schemas ----------

class AvailabilityRequest(BaseModel):
    booking_date: date
    booking_time: time
    party_size: int
    service_name: Optional[str] = "Cena"


class AvailabilityResponse(BaseModel):
    available: bool
    tables_free: int


class CreateBookingRequest(BaseModel):
    customer_name: str
    phone: Optional[str] = None
    booking_date: date
    booking_time: time
    party_size: int
    service_name: Optional[str] = "Cena"
    notes: Optional[str] = None


class ModifyBookingRequest(BaseModel):
    booking_date: Optional[date] = None
    booking_time: Optional[time] = None
    party_size: Optional[int] = None
    customer_name: Optional[str] = None


# ---------- Helpers ----------

def _overlapping_bookings(session: Session, booking_date: date, booking_time: time, duration_min: int) -> List[Booking]:
    start = datetime.combine(booking_date, booking_time)
    end = start + timedelta(minutes=duration_min)
    all_bookings = session.exec(
        select(Booking).where(Booking.booking_date == booking_date, Booking.status == "confirmed")
    ).all()
    overlapping = []
    for b in all_bookings:
        b_start = datetime.combine(b.booking_date, b.booking_time)
        b_end = b_start + timedelta(minutes=duration_min)
        if start < b_end and end > b_start:
            overlapping.append(b)
    return overlapping


# ---------- Endpoints usados por el orquestador (tool calling) ----------

@app.post("/tools/check_availability", response_model=AvailabilityResponse)
def check_availability(req: AvailabilityRequest, session: Session = Depends(get_session)):
    service = session.exec(select(Service).where(Service.name == req.service_name)).first()
    duration = service.duration_min if service else 90

    total_tables = session.exec(select(Resource).where(Resource.resource_type == "table")).all()
    # cuántas mesas necesitas según el tamaño del grupo (capacidad 4 por mesa)
    tables_needed = max(1, -(-req.party_size // 4))  # ceil division

    overlapping = _overlapping_bookings(session, req.booking_date, req.booking_time, duration)
    tables_used = sum(max(1, -(-b.party_size // 4)) for b in overlapping)
    tables_free = len(total_tables) - tables_used

    return AvailabilityResponse(available=tables_free >= tables_needed, tables_free=tables_free)


@app.post("/tools/create_reservation")
def create_reservation(req: CreateBookingRequest, session: Session = Depends(get_session)):
    avail = check_availability(
        AvailabilityRequest(
            booking_date=req.booking_date,
            booking_time=req.booking_time,
            party_size=req.party_size,
            service_name=req.service_name,
        ),
        session,
    )
    if not avail.available:
        raise HTTPException(status_code=409, detail="No hay disponibilidad para esa franja")

    service = session.exec(select(Service).where(Service.name == req.service_name)).first()

    booking = Booking(
        customer_name=req.customer_name,
        phone=req.phone,
        booking_date=req.booking_date,
        booking_time=req.booking_time,
        party_size=req.party_size,
        service_id=service.id if service else None,
        notes=req.notes,
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking


@app.patch("/tools/modify_reservation/{booking_id}")
def modify_reservation(booking_id: int, req: ModifyBookingRequest, session: Session = Depends(get_session)):
    booking = session.get(Booking, booking_id)
    if not booking or booking.status != "confirmed":
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    for field, value in req.dict(exclude_unset=True).items():
        setattr(booking, field, value)

    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking


@app.patch("/tools/cancel_reservation/{booking_id}")
def cancel_reservation(booking_id: int, session: Session = Depends(get_session)):
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    booking.status = "cancelled"
    session.add(booking)
    session.commit()
    return {"ok": True}


@app.get("/tools/find_reservation")
def find_reservation(customer_name: str, booking_date: Optional[date] = None, session: Session = Depends(get_session)):
    query = select(Booking).where(Booking.customer_name.ilike(f"%{customer_name}%"), Booking.status == "confirmed")
    if booking_date:
        query = query.where(Booking.booking_date == booking_date)
    return session.exec(query).all()


# ---------- Endpoints para el panel web ----------

@app.get("/bookings", response_model=List[Booking])
def list_bookings(booking_date: Optional[date] = None, session: Session = Depends(get_session)):
    query = select(Booking).where(Booking.status == "confirmed")
    if booking_date:
        query = query.where(Booking.booking_date == booking_date)
    return session.exec(query.order_by(Booking.booking_date, Booking.booking_time)).all()


@app.post("/call_logs")
def log_call(log: CallLog, session: Session = Depends(get_session)):
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
