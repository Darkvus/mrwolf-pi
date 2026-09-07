"""
Orquestador de llamadas Mr. Wolf.

Flujo por cada llamada entrante (evento StasisStart de Asterisk ARI):
  1. Contesta el canal.
  2. Bucle: graba turno del cliente (silencio detecta fin) -> STT -> LLM (+ tools) -> TTS -> reproduce.
  3. Si el LLM pide transfer_to_human, cuelga el bucle IA y origina la llamada de transferencia.

Requiere Asterisk con ARI habilitado (ari.conf) y una app Stasis llamada "mrwolf"
referenciada desde el dialplan (extensions.conf) para el canal Mobile (chan_mobile).
"""

import os
import time
import logging

import ari

from stt import transcribe
from tts import synthesize
from llm import chat
from tools import execute_tool
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("orchestrator")

ARI_URL = os.environ.get("ARI_URL", "http://localhost:8088")
ARI_USER = os.environ.get("ARI_USER", "orchestrator")
ARI_PASS = os.environ.get("ARI_PASS", "changeme")
ARI_APP = os.environ.get("ARI_APP", "mrwolf")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")
TENANT_ID = os.environ.get("TENANT_ID", "mrwolf-pizzeria")
HUMAN_TRANSFER_NUMBER = os.environ.get("HUMAN_TRANSFER_NUMBER", "")

with open("/app/prompts/base_es.txt", encoding="utf-8") as f:
    BASE_PROMPT = f.read()
with open("/app/prompts/restaurant.txt", encoding="utf-8") as f:
    VERTICAL_PROMPT = f.read()

SYSTEM_PROMPT = BASE_PROMPT + "\n" + VERTICAL_PROMPT


def record_customer_turn(channel) -> str:
    """Graba hasta detectar silencio (maxSilenceSeconds) y devuelve la ruta del audio grabado."""
    rec_name = f"turn-{channel.id}-{int(time.time())}"
    recording = channel.record(
        name=rec_name,
        format="wav",
        maxDurationSeconds=15,
        maxSilenceSeconds=2,
        beep=False,
        ifExists="overwrite",
    )
    # Espera activa a que termine la grabación
    while True:
        time.sleep(0.3)
        status = recording.get()["state"]
        if status in ("done", "failed"):
            break
    return f"/var/spool/asterisk/recording/{rec_name}.wav"


def run_conversation(channel):
    channel.answer()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    greeting = "Hola, Mr. Wolf, ¿en qué puedo ayudarte?"
    play_text(channel, greeting)
    messages.append({"role": "assistant", "content": greeting})

    transcript_log = [f"IA: {greeting}"]
    last_booking_id = None

    for _ in range(20):  # límite de turnos por seguridad
        audio_path = record_customer_turn(channel)
        user_text = transcribe(audio_path)
        if not user_text.strip():
            play_text(channel, "Perdona, no te he escuchado bien, ¿puedes repetirlo?")
            continue

        transcript_log.append(f"Cliente: {user_text}")
        messages.append({"role": "user", "content": user_text})

        result = chat(messages)

        if result["type"] == "tool_call":
            tool_result = execute_tool(result["name"], result["args"])

            if result["name"] == "transfer_to_human" or tool_result.get("action") == "transfer":
                play_text(channel, "Un momento, te paso con una persona del restaurante.")
                transfer_call(channel)
                break

            if "id" in tool_result:
                last_booking_id = tool_result["id"]

            messages.append({
                "role": "tool",
                "name": result["name"],
                "content": str(tool_result),
            })
            # segunda pasada: que el LLM redacte la respuesta hablada con el resultado de la tool
            follow_up = chat(messages)
            reply_text = follow_up.get("content", "Vale, un momento.")
        else:
            reply_text = result["content"]

        transcript_log.append(f"IA: {reply_text}")
        messages.append({"role": "assistant", "content": reply_text})
        play_text(channel, reply_text)

        if "adiós" in user_text.lower() or "gracias, hasta luego" in user_text.lower():
            break

    log_call(last_booking_id, "\n".join(transcript_log))
    try:
        channel.hangup()
    except Exception:
        pass


def play_text(channel, text: str):
    wav_path = synthesize(text)
    playback = channel.play(media=f"sound:{wav_path.replace('.wav', '')}")
    while True:
        time.sleep(0.2)
        try:
            if playback.get()["state"] == "done":
                break
        except Exception:
            break


def transfer_call(channel):
    if not HUMAN_TRANSFER_NUMBER:
        log.warning("HUMAN_TRANSFER_NUMBER no configurado, no se puede transferir")
        return
    channel.setChannelVar(variable="TRANSFER_TO", value=HUMAN_TRANSFER_NUMBER)
    channel.continueInDialplan(context="transfer", extension="s", priority=1)


def log_call(booking_id, transcript):
    try:
        requests.post(
            f"{API_BASE_URL}/call_logs",
            json={"tenant_id": TENANT_ID, "booking_id": booking_id, "transcript": transcript, "outcome": "completed"},
            timeout=5,
        )
    except Exception as e:
        log.error(f"No se pudo guardar el log de llamada: {e}")


def on_start(channel, ev):
    log.info(f"Nueva llamada entrante: {channel.id}")
    try:
        run_conversation(channel)
    except Exception:
        log.exception("Error en la conversación")
        try:
            channel.hangup()
        except Exception:
            pass


def main():
    client = ari.connect(ARI_URL, ARI_USER, ARI_PASS)
    client.on_channel_event("StasisStart", on_start)
    log.info("Orquestador conectado a Asterisk ARI, esperando llamadas...")
    client.run(apps=ARI_APP)


if __name__ == "__main__":
    main()
