import os
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")

TOOL_DEFINITIONS = [
    {
        "name": "check_availability",
        "description": "Comprueba si hay disponibilidad para una reserva en fecha/hora/personas dadas.",
        "parameters": {
            "type": "object",
            "properties": {
                "booking_date": {"type": "string", "description": "YYYY-MM-DD"},
                "booking_time": {"type": "string", "description": "HH:MM"},
                "party_size": {"type": "integer"},
            },
            "required": ["booking_date", "booking_time", "party_size"],
        },
    },
    {
        "name": "create_reservation",
        "description": "Crea una reserva confirmada.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "phone": {"type": "string"},
                "booking_date": {"type": "string"},
                "booking_time": {"type": "string"},
                "party_size": {"type": "integer"},
            },
            "required": ["customer_name", "booking_date", "booking_time", "party_size"],
        },
    },
    {
        "name": "modify_reservation",
        "description": "Modifica una reserva existente por su id.",
        "parameters": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "integer"},
                "booking_date": {"type": "string"},
                "booking_time": {"type": "string"},
                "party_size": {"type": "integer"},
            },
            "required": ["booking_id"],
        },
    },
    {
        "name": "cancel_reservation",
        "description": "Cancela una reserva existente por su id.",
        "parameters": {
            "type": "object",
            "properties": {"booking_id": {"type": "integer"}},
            "required": ["booking_id"],
        },
    },
    {
        "name": "find_reservation",
        "description": "Busca reservas existentes por nombre del cliente.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "booking_date": {"type": "string"},
            },
            "required": ["customer_name"],
        },
    },
    {
        "name": "transfer_to_human",
        "description": "Transfiere la llamada a una persona real. Úsalo si el cliente lo pide explícitamente o si no puedes resolver la petición.",
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


def execute_tool(name: str, args: dict) -> dict:
    if name == "check_availability":
        r = requests.post(f"{API_BASE_URL}/tools/check_availability", json=args, timeout=5)
        return r.json()

    if name == "create_reservation":
        r = requests.post(f"{API_BASE_URL}/tools/create_reservation", json=args, timeout=5)
        if r.status_code == 409:
            return {"error": "no_availability"}
        return r.json()

    if name == "modify_reservation":
        booking_id = args.pop("booking_id")
        r = requests.patch(f"{API_BASE_URL}/tools/modify_reservation/{booking_id}", json=args, timeout=5)
        return r.json()

    if name == "cancel_reservation":
        r = requests.patch(f"{API_BASE_URL}/tools/cancel_reservation/{args['booking_id']}", timeout=5)
        return r.json()

    if name == "find_reservation":
        r = requests.get(f"{API_BASE_URL}/tools/find_reservation", params=args, timeout=5)
        return r.json()

    if name == "transfer_to_human":
        return {"action": "transfer", "reason": args.get("reason")}

    return {"error": f"unknown_tool:{name}"}
