# Mr. Wolf — IA telefónica de reservas (Raspberry Pi 4)

MVP: llamada entrante por Bluetooth desde tu Android con SIM SIMYO → Asterisk (`chan_mobile`) → STT (Whisper) → LLM local (Qwen, tool-calling) → gestión de reservas → TTS (Piper) → respuesta hablada.

## 0. Requisitos en la Raspberry Pi

- Raspberry Pi OS 64-bit (Bookworm), RPi4 8GB.
- Docker + Docker Compose (`curl -fsSL https://get.docker.com | sh`).
- Bluetooth activo (`bluetoothctl`), BlueZ instalado (viene por defecto en Raspberry Pi OS).
- Tu Android antiguo con la SIM de SIMYO, con **Bluetooth "manos libres" (HFP)** activable — normalmente aparece al emparejar como "dispositivo de coche/altavoz".

## 1. Emparejar el Android por Bluetooth

```bash
bluetoothctl
power on
agent on
scan on
# localiza tu Android en la lista, copia su MAC (XX:XX:XX:XX:XX:XX)
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
```

En el Android, acepta el emparejamiento y **confirma el perfil "Audio de llamadas / manos libres"** si te lo pregunta (no solo "transferencia de archivos").

Edita `asterisk/config/chan_mobile.conf` y pon esa MAC real en `address=`.

## 2. Descargar los modelos (se montan como volumen, no van en la imagen)

```bash
cd mrwolf-pi/models

# LLM: Qwen2.5-1.5B-Instruct cuantizado (~1GB)
wget https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# Whisper "small" lo descarga faster-whisper solo la primera vez (se cachea en el volumen)

# Piper: voz española
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_10246/medium/es_ES-mls_10246-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_10246/medium/es_ES-mls_10246-medium.onnx.json
```

## 3. Configurar variables de entorno

```bash
cd mrwolf-pi
cp .env.example .env
# edita .env y pon un ARI_PASS seguro
```

En `docker-compose.yml`, añade también `HUMAN_TRANSFER_NUMBER=+34XXXXXXXXX` (tu móvil) en las `environment:` del servicio `orchestrator` cuando quieras probar la transferencia.

## 4. Levantar todo

```bash
docker compose up --build -d
docker compose logs -f asterisk       # comprueba que chan_mobile detecta el Android
docker compose logs -f orchestrator   # comprueba conexión ARI: "esperando llamadas..."
```

Dentro del contenedor de Asterisk puedes verificar el estado del canal Bluetooth:

```bash
docker exec -it mrwolf-asterisk asterisk -rx "mobile show devices"
```

Debe aparecer tu Android como `Connected`.

## 5. Probar

Llama desde otro móvil al número SIMYO. Deberías oír el saludo de la IA, poder pedir una reserva ("quiero una mesa para 4 mañana a las 9"), y que confirme los datos.

Consulta las reservas creadas en el panel web:

```
http://<ip-de-tu-raspberry>:8000/panel/
```

(Para acceder desde fuera de casa sin abrir puertos, instala **Tailscale** en la Raspberry y en tu móvil, y usa la IP de Tailscale en vez de la IP local.)

## 6. Notas y limitaciones conocidas de este MVP

- `chan_mobile` es un módulo antiguo: si pierde la conexión Bluetooth, reinicia el contenedor de Asterisk (`docker compose restart asterisk`) o añade un healthcheck que lo haga automáticamente.
- La calidad de audio es narrowband (8kHz) por naturaleza de HFP — normal, no es un bug.
- Si el LLM tarda demasiado en responder (>3-4s), reduce `max_tokens` en `llm.py` o prueba una cuantización más agresiva (Q4_0) del modelo.
- Cuando quieras pasar a producción real, sustituye el servicio `asterisk` (chan_mobile) por un trunk SIP contra un gateway GSM dedicado (GoIP-1) — el resto del stack (`api`, `orchestrator`, prompts, base de datos) no cambia.

## Estructura

```
mrwolf-pi/
├── docker-compose.yml
├── .env.example
├── asterisk/           # Dockerfile (compila Asterisk+chan_mobile) + config/
├── orchestrator/        # STT + LLM (tool-calling) + TTS + puente ARI
├── local-api/            # FastAPI + SQLite: reservas + panel web (/panel/)
├── prompts/              # system prompt base + vertical (restaurante)
├── models/               # pesos de LLM/Whisper/Piper (no versionar, pesan mucho)
└── data/                 # mrwolf.db (SQLite)
```
