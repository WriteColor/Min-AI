"""services/audio_service.py — Audio capture, playback, and realtime streaming"""

import asyncio
import json
import traceback
from pathlib import Path

import numpy as np
import sounddevice as sd


class AudioService:
    def __init__(self, ui, tts_service, get_llm_provider=None, get_api_key=None,
                 get_live_model=None, vosk_recognizer=None, local_command_queue=None):
        self.ui = ui
        self.tts_service = tts_service

        # Session & loop — assigned when connection is opened
        self.session = None
        self.loop = None

        # Queues
        self.out_queue = None
        self.audio_in_queue = None
        self._local_command_queue = local_command_queue

        # Events
        self._turn_done_event = None
        self._stop_requested = None

        # Wake word / sleep state
        self.vosk_recognizer = vosk_recognizer
        self.is_sleeping = False

        # Internal state
        self._last_speak_time = 0.0
        self._api_1011_tool = None
        self._first_chunk_flag = True

        # Callbacks provided by MinLive
        self._get_llm_provider = get_llm_provider
        self._get_api_key = get_api_key
        self._get_live_model = get_live_model
        self._execute_tool_func = None
        self._fire_phrase_triggers_func = None

    def set_execute_tool_func(self, func):
        self._execute_tool_func = func

    def set_fire_phrase_triggers_func(self, func):
        self._fire_phrase_triggers_func = func

    def assign_session(self, session, loop, out_queue, audio_in_queue, turn_done_event, stop_requested):
        self.session = session
        self.loop = loop
        self.out_queue = out_queue
        self.audio_in_queue = audio_in_queue
        self._turn_done_event = turn_done_event
        self._stop_requested = stop_requested

    def _drain_audio_queue(self):
        if self.audio_in_queue:
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except Exception:
                    pass

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def listen_audio(self):
        print("[MIN] Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            import time
            now = time.time()
            with self.tts_service._speaking_lock:
                min_speaking = self.tts_service._is_speaking
                if min_speaking:
                    self._last_speak_time = now

            provider = self._get_llm_provider() if self._get_llm_provider else "gemini"

            if getattr(self, "is_sleeping", False):
                if getattr(self, "vosk_recognizer", None):
                    audio_data = indata.tobytes()
                    if self.vosk_recognizer.AcceptWaveform(audio_data):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "")
                        if "min" in text.lower():
                            self.is_sleeping = False
                            self.ui.set_state("LISTENING")
                            self.ui.write_log("SYS: \U0001f7e0 \u00a1Despierto!")
                            try:
                                import winsound
                                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                            except:
                                pass
                return

            is_cooling_down = (now - getattr(self, "_last_speak_time", 0.0)) < 0.8
            if not min_speaking and not is_cooling_down and not self.ui.muted:
                from services.audio.pipeline import AudioPipeline
                if not hasattr(self, "audio_pipeline"):
                    self.audio_pipeline = AudioPipeline()

                result = self.audio_pipeline.process_chunk(indata)
                rms = result.get("rms", 0.0)
                action = result.get("action", "silence")
                self.ui.set_audio_level(min(1.0, rms * 18))

                if action == "overflow":
                    text = self.audio_pipeline.flush_buffer()
                    if text:
                        self.ui.write_log(f"Tú (STT Local): {text}")
                        loop.call_soon_threadsafe(self._local_command_queue.put_nowait, text)
                elif action == "wake":
                    ww = result.get("wake_word")
                    if ww:
                        self.ui.write_log(f"SYS: ¡Wake word '{ww}' detectado!")
                        self.is_sleeping = False
                        self.ui.set_state("LISTENING")
                        try:
                            import winsound
                            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                        except Exception:
                            pass

                if provider != "gemini" and getattr(self, "vosk_recognizer", None) and action in ("accumulate", "silence"):
                    audio_bytes = indata.tobytes()
                    if self.vosk_recognizer.AcceptWaveform(audio_bytes):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "").strip()
                        if text:
                            self.ui.write_log(f"Tú (Voz Local): {text}")
                            loop.call_soon_threadsafe(self._local_command_queue.put_nowait, text)
                elif provider == "gemini" and action in ("accumulate", "silence"):
                    def _safe_put(q, item):
                        try:
                            q.put_nowait(item)
                        except Exception:
                            pass
                    loop.call_soon_threadsafe(
                        _safe_put, self.out_queue, {"data": indata.tobytes(), "mime_type": "audio/pcm"}
                    )
            elif min_speaking:
                try:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.ui.set_audio_level(min(1.0, rms * 15))
                except Exception:
                    pass

        try:
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=256,
                callback=callback,
            ):
                print("[MIN] Mic stream open")
                while True:
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"[MIN] \u274c Mic: {e}")
            raise

    async def receive_audio(self):
        from services._core.helpers import _clean_transcript

        print("[MIN] Recv started")
        out_buf, in_buf = [], []
        _first_chunk = True
        _last_tool = None

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._stop_requested.is_set():
                            self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                                if _first_chunk:
                                    self.ui.clear_min_response()
                                    _first_chunk = False
                                self.ui.stream_min_chunk(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self._stop_requested.clear()
                            if self._turn_done_event:
                                self._turn_done_event.set()
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"T\u00fa: {full_in}")
                                if self._fire_phrase_triggers_func:
                                    self._fire_phrase_triggers_func(full_in)
                            in_buf = []
                            out_buf = []
                            _first_chunk = True

                    if response.text:
                        txt = response.text
                        if txt:
                            if _first_chunk:
                                self.ui.clear_min_response()
                                _first_chunk = False
                            out_buf.append(txt)
                            self.ui.stream_min_chunk(txt)

                    if response.tool_call:
                        self.ui.clear_min_response()
                        _first_chunk = True
                        fcs = response.tool_call.function_calls
                        for fc in fcs:
                            print(f"[MIN] Tool call: {fc.name}")
                            _last_tool = fc.name

                        if len(fcs) > 1:
                            tasks = [asyncio.create_task(self._execute_tool_func(fc)) for fc in fcs]
                            fn_responses = list(await asyncio.gather(*tasks))
                        else:
                            fn_responses = [await self._execute_tool_func(fcs[0])]
                        try:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
                            _last_tool = None
                        except Exception as tool_err:
                            print(f"[MIN] \u274c send_tool_response failed: {tool_err}")
                            raise
                        for fn_resp in fn_responses:
                            if hasattr(fn_resp, 'response') and isinstance(fn_resp.response, dict):
                                text = fn_resp.response.get('result', '')
                            elif isinstance(fn_resp.response, str):
                                text = fn_resp.response
                            else:
                                text = str(fn_resp.response) if fn_resp.response else ''
                            if text and isinstance(text, str) and len(text) > 1:
                                self.ui.clear_min_response()
                                self.ui.stream_min_chunk(text)
                                self.ui.broadcast({"type": "text", "value": text})
                                if not self.ui.muted:
                                    asyncio.create_task(self.tts_service.speak_local(text))
        except Exception as e:
            msg = str(e)
            code = getattr(e, "status_code", 0) or getattr(e, "code", 0) or 0
            if code == 1011 or "1011" in msg or "Internal error" in msg:
                tool_info = f" durante '{_last_tool}'" if _last_tool else ""
                print(f"[MIN] \u26a1 API 1011{tool_info} \u2014 reconectando...")
                self._api_1011_tool = _last_tool
            else:
                print(f"[MIN] Recv Error: {e}")
                traceback.print_exc()
            raise

    async def play_audio(self):
        print("[MIN] Play started")

        stream = sd.RawOutputStream(
            samplerate=24000,
            channels=1,
            dtype="int16",
            blocksize=480,
        )
        stream.start()

        _jitter_buf: list[bytes] = []
        _JITTER_TARGET = 3
        prebuffering = True

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.05
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        while _jitter_buf:
                            buffered = _jitter_buf.pop(0)
                            try:
                                play_data = np.frombuffer(buffered, dtype=np.int16)
                                rms = float(np.sqrt(np.mean(play_data.astype(np.float32) ** 2))) / 32768.0
                                self.ui.set_audio_level(min(1.0, rms * 25))
                            except Exception:
                                pass
                            await asyncio.to_thread(stream.write, buffered)
                        self.tts_service.set_speaking(False)
                        self._turn_done_event.clear()
                        prebuffering = True
                    continue

                self.tts_service.set_speaking(True)
                _jitter_buf.append(chunk)

                if prebuffering:
                    if len(_jitter_buf) >= _JITTER_TARGET:
                        prebuffering = False

                if not prebuffering:
                    buffered = _jitter_buf.pop(0)
                    try:
                        play_data = np.frombuffer(buffered, dtype=np.int16)
                        rms = float(np.sqrt(np.mean(play_data.astype(np.float32) ** 2))) / 32768.0
                        self.ui.set_audio_level(min(1.0, rms * 25))
                    except Exception:
                        pass
                    await asyncio.to_thread(stream.write, buffered)
        except Exception as e:
            print(f"[MIN] \u274c Play: {e}")
            raise
        finally:
            self.tts_service.set_speaking(False)
            stream.stop()
            stream.close()

    async def process_audio_file(self, path: str):
        """Transcribe and analyze an audio file via Gemini (separate from realtime session)."""
        from google import genai
        api_key = self._get_api_key() if self._get_api_key else ""
        live_model = self._get_live_model() if self._get_live_model else "models/gemini-2.5-flash-native-audio-preview-12-2025"

        try:
            p = Path(path)
            if not p.exists():
                self.ui.write_log(f"\u274c Archivo no encontrado: {path}")
                return

            self.ui.set_state("THINKING")
            client = genai.Client(api_key=api_key)

            loop = asyncio.get_event_loop()

            def _analyze():
                audio_file = client.files.upload(file=p)
                prompt = (
                    "Transcribe este archivo de audio con total precisi\u00f3n. "
                    "Luego, analiza su contenido y proporciona una respuesta coherente."
                )
                response = client.models.generate_content(
                    model=live_model,
                    contents=[audio_file, prompt]
                )
                return response.text

            resp_text = await loop.run_in_executor(None, _analyze)
            self.ui.write_log("\U0001f508 An\u00e1lisis de archivo de audio completado.")
            self.ui.clear_min_response()
            self.ui.stream_min_chunk(resp_text)

            await self.tts_service.speak_local(resp_text)
        except Exception as e:
            self.ui.write_log(f"\u274c Error procesando audio: {e}")
            traceback.print_exc()

        self.ui.set_state("LISTENING")
