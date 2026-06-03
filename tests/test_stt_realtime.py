# -*- coding: utf-8 -*-
"""
test_stt_realtime.py — Realtime STT test with live transcription log
================================================================

Escucha el micrófono y transcribe en tiempo real lo que dices usando STTEngine.
Guarda todo en logs/stt_realtime_YYYYMMDD_HHMMSS.txt con timestamps.

Uso:
    python tests/test_stt_realtime.py

Para detener: Ctrl+C
"""

import asyncio
import sys
import sounddevice as sd
import numpy as np
from datetime import datetime
from pathlib import Path

# Fix paths to allow importing from parent directory
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.audio.stt import STTEngine

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / f"stt_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# ── STT Setup ────────────────────────────────────────────────────────
print("[STT] Iniciando motor de transcripcion STTEngine...")

stt = STTEngine(
    model_path="config/vosk_model",
    sample_rate=16000,
    force_load=True
)

if not stt.available:
    print("[STT] ERROR: El motor STT Vosk no está disponible. Descarga vosk_model en config/vosk_model.")
    sys.exit(1)

print("[STT] Vosk cargado OK")

SAMPLE_RATE = 16000
CHUNK_SIZE = 4096  # ~256ms per chunk

# ── Log setup ────────────────────────────────────────────────────────────────
log_file = LOG_FILE
log_file.write_text(
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === INICIO TEST STT REALETIME ===\n"
    f"Motor: Vosk (STTEngine)\n"
    f"Sample rate: {SAMPLE_RATE} Hz\n"
    f"Chunk size: {CHUNK_SIZE}\n"
    f"{'='*60}\n\n",
    encoding="utf-8"
)

last_transcript = ""
last_log_time = datetime.now()

print(f"\n[STT] Log: {log_file.name}")
print(f"[STT] Escuchando... (Ctrl+C para detener)\n")


def callback(indata, frames, time_info, status):
    global last_transcript, last_log_time

    audio_data = indata[:, 0].copy()  # mono
    audio_bytes = audio_data.astype(np.int16).tobytes()

    # Transcribe using stt.transcribe_bytes
    text = stt.transcribe_bytes(audio_bytes)

    if text and text != last_transcript and len(text) > 1:
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        elapsed = (now - last_log_time).total_seconds()
        line = f"[{timestamp}] ({elapsed:.1f}s) {text}\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)

        print(f"  [{timestamp}] {text}")
        last_transcript = text
        last_log_time = now


async def main():
    print("=" * 50)
    print("STT REALTIME TEST USING STTENGINE")
    print("=" * 50)
    print(f"Log:   {log_file}")
    print("Speak now... (Ctrl+C para detener)\n")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=callback
        ):
            print("[STT] Mic activa. Habla ahora...")
            # Keep running
            while True:
                await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[STT] Detenido.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{now}] === FIN TEST STT ===\n")
        print(f"[STT] Log guardado: {log_file}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass