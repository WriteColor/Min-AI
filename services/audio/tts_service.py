"""services/tts_service.py — Text-to-Speech using Kokoro-82M or edge-tts fallback"""

import os
import re
import asyncio
import threading
import tempfile
import numpy as np
import sounddevice as sd
from services.audio.tts import KokoroEngine
from services.audio.sentence_segmenter import SentenceSegmenter

def _clean_tts_text(text: str) -> str:
    """Strip <think>...</think> thinking tags from text for clean TTS output."""
    from services._core.helpers import clean_think_blocks
    return clean_think_blocks(text)


class TTSService:
    def __init__(self, ui):
        self.ui = ui
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._stop_requested = asyncio.Event()
        self._loop = None
        self._play_lock = asyncio.Lock()

        # Kokoro engine instance
        self.kokoro_engine = KokoroEngine()

        # Text segments queue and playback task
        self._text_queue = asyncio.Queue()
        self._playback_task = None

        # Buffers for sentence segmentation and streaming think tag filter
        self.buffer = ""
        self._raw_stream_buf = ""
        self._in_think_block = False

        # Streaming sentence segmenter for real-time TTS
        self._segmenter = SentenceSegmenter(min_segment_length=3)

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
            if not value:
                self._stop_requested.clear()

    def start_stream(self):
        """Starts a new streaming session."""
        print("[TTS] Starting new audio stream...")
        self.stop_playback()

        self.set_speaking(True)
        self._stop_requested.clear()
        self.buffer = ""
        self._raw_stream_buf = ""
        self._in_think_block = False
        self._segmenter.reset()

        self._ensure_playback_task()

    def feed_token(self, token: str):
        """Feeds a token into the streaming buffer, segments sentences, and schedules speech."""
        if self._stop_requested.is_set() or not self._is_speaking:
            return

        # 1. Filter out thinking tags
        clean_text = self._filter_thinking(token)
        if not clean_text:
            return

        # 2. Process through streaming sentence segmenter
        segments = self._segmenter.process(clean_text)
        for segment in segments:
            if segment.strip():
                self._text_queue.put_nowait(segment)

    def end_stream(self):
        """Signals the end of the streaming response and flushes any remaining text."""
        if not self._is_speaking:
            return

        # Flush remaining text from think filter
        remaining_clean = self._filter_thinking("")
        if remaining_clean:
            segments = self._segmenter.process(remaining_clean)
            for segment in segments:
                if segment.strip():
                    self._text_queue.put_nowait(segment)

        # Flush any remaining buffered text from segmenter
        remaining_segments = self._segmenter.flush()
        for segment in remaining_segments:
            if segment.strip():
                self._text_queue.put_nowait(segment)

        # Signal the worker to exit after finishing the queue
        self._text_queue.put_nowait(None)

    def stop_playback(self):
        """Immediately interrupts playback and clears queue."""
        print("[TTS] Stopping playback...")
        self._stop_requested.set()
        self.set_speaking(False)
        self.clear_queue()
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()

    def clear_queue(self):
        """Drains the text queue."""
        while not self._text_queue.empty():
            try:
                self._text_queue.get_nowait()
                self._text_queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break

    def _ensure_playback_task(self):
        if self._playback_task is None or self._playback_task.done():
            self._playback_task = asyncio.create_task(self._synthesis_and_playback_loop())

    async def _generate_audio_samples(self, text: str, voice: str, speed: float) -> tuple[np.ndarray, int]:
        """Generate audio samples trying Edge-TTS first (online), falling back to Kokoro (local)."""
        rate_str = f"+{int((speed - 1.0) * 15)}%" if speed >= 1.0 else f"-{int((1.0 - speed) * 15)}%"
        voices_map = {
            "Aoede": "es-US-PalomaNeural",
            "Kore": "es-MX-DaliaNeural",
            "Leda": "es-ES-ElviraNeural",
            "Zephyr": "es-US-AlonsoNeural",
            "Charon": "es-MX-JorgeNeural",
            "Puck": "es-ES-AlvaroNeural",
            "Fenrir": "es-AR-TomasNeural",
            "Orus": "es-CL-LorenzoNeural"
        }
        voice_code = voices_map.get(voice, "es-US-PalomaNeural")
        
        try:
            import edge_tts
            import soundfile as sf
            
            temp_path = os.path.join(tempfile.gettempdir(), f"min_stream_tts_{os.getpid()}_{threading.get_ident()}.mp3")
            communicate = edge_tts.Communicate(text, voice_code, rate=rate_str)
            await communicate.save(temp_path)
            
            def read_file():
                try:
                    data, fs = sf.read(temp_path)
                    return data, fs
                finally:
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                        
            samples, sample_rate = await asyncio.get_running_loop().run_in_executor(None, read_file)
            print(f"[TTS] Generated segment via Edge-TTS ({voice_code})")
            return samples, sample_rate
            
        except Exception as edge_err:
            print(f"[TTS] Edge-TTS failed ({edge_err}). Falling back to local Kokoro...")
            samples, sample_rate = await asyncio.to_thread(
                self.kokoro_engine.generate, text, voice, speed
            )
            print(f"[TTS] Generated segment via local Kokoro (voice={voice})")
            return samples, sample_rate

    async def _synthesis_and_playback_loop(self):
        print("[TTS] Playback loop started.")
        stream = None
        current_sr = 24000  # Default Kokoro sample rate
        
        try:
            stream = sd.OutputStream(
                samplerate=current_sr,
                channels=1,
                dtype="float32",
                blocksize=512
            )
            stream.start()
            
            while True:
                item = await self._text_queue.get()
                if item is None:
                    self._text_queue.task_done()
                    break

                if not self._is_speaking or self._stop_requested.is_set():
                    self._text_queue.task_done()
                    continue

                from core.config_manager import get_config
                cfg = get_config()
                speed = cfg.speech_rate or 1.0
                voice = cfg.min_voice or "Aoede"

                from services._core.helpers import strip_markdown
                clean_seg = strip_markdown(item).strip()
                if clean_seg:
                    try:
                        samples, sample_rate = await self._generate_audio_samples(clean_seg, voice, speed)
                        
                        if sample_rate != current_sr:
                            print(f"[TTS] Sample rate changed from {current_sr} to {sample_rate}. Recreating stream...")
                            stream.stop()
                            stream.close()
                            current_sr = sample_rate
                            stream = sd.OutputStream(
                                samplerate=current_sr,
                                channels=1,
                                dtype="float32",
                                blocksize=512
                            )
                            stream.start()
                        
                        samples = samples.astype(np.float32)
                        if samples.ndim > 1:
                            samples = np.mean(samples, axis=1)
                            
                        block_size = 512
                        idx = 0
                        n = len(samples)
                        
                        loop = asyncio.get_running_loop()
                        
                        def write_chunk():
                            nonlocal idx
                            while idx < n and self._is_speaking and not self._stop_requested.is_set():
                                chunk = samples[idx : idx + block_size]
                                if len(chunk) < block_size:
                                    pad = np.zeros(block_size - len(chunk), dtype=np.float32)
                                    chunk = np.concatenate([chunk, pad])
                                
                                try:
                                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                                    self.ui.set_audio_level(min(1.0, rms * 25.0))
                                except Exception:
                                    pass
                                
                                stream.write(chunk)
                                idx += block_size
                                
                        await loop.run_in_executor(None, write_chunk)
                        
                    except Exception as e:
                        print(f"[TTS] Generation/playback error: {e}")

                self._text_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[TTS] Playback loop crash: {e}")
        finally:
            self.set_speaking(False)
            if stream:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
            print("[TTS] Playback loop ended.")

    def _filter_thinking(self, text: str) -> str:
        self._raw_stream_buf += text
        clean_text = ""
        while True:
            if self._in_think_block:
                idx = self._raw_stream_buf.find("</think>")
                if idx != -1:
                    self._raw_stream_buf = self._raw_stream_buf[idx + len("</think>"):]
                    self._in_think_block = False
                else:
                    keep_len = 0
                    for i in range(1, 8):
                        suffix = self._raw_stream_buf[-i:]
                        if "</think>".startswith(suffix):
                            keep_len = i
                    if keep_len > 0:
                        self._raw_stream_buf = self._raw_stream_buf[-keep_len:]
                    else:
                        self._raw_stream_buf = ""
                    break
            else:
                idx = self._raw_stream_buf.find("<think>")
                if idx != -1:
                    clean_text += self._raw_stream_buf[:idx]
                    self._raw_stream_buf = self._raw_stream_buf[idx + len("<think>"):]
                    self._in_think_block = True
                else:
                    keep_len = 0
                    for i in range(1, 7):
                        suffix = self._raw_stream_buf[-i:]
                        if "<think>".startswith(suffix):
                            keep_len = i
                    if keep_len > 0:
                        clean_text += self._raw_stream_buf[:-keep_len]
                        self._raw_stream_buf = self._raw_stream_buf[-keep_len:]
                    else:
                        clean_text += self._raw_stream_buf
                        self._raw_stream_buf = ""
                    break
        return clean_text



    async def speak_local(self, text: str):
        """TTS local robusto utilizando Kokoro o edge-tts fallback."""
        from core.config_manager import get_config
        cfg = get_config()

        text = _clean_tts_text(text)
        if not text.strip():
            return

        # Si el proveedor activo es gemini, usar edge_tts
        if cfg.active_provider == "gemini":
            if self._is_speaking:
                self._stop_requested.set()
                for _ in range(20):
                    if not self._is_speaking:
                        break
                    await asyncio.sleep(0.05)

            async with self._play_lock:
                self._stop_requested.clear()
                self.set_speaking(True)
                try:
                    temp_path = os.path.join(tempfile.gettempdir(), f"min_local_tts_{os.getpid()}.mp3")
                    from services._core.helpers import strip_markdown
                    clean_text = strip_markdown(text)

                    rate = f"+{int((cfg.speech_rate or 1.0) * 15)}%" if cfg.speech_rate >= 1.0 else f"-{int((1.0 - cfg.speech_rate) * 15)}%"
                    voices = {
                        "Aoede": "es-US-PalomaNeural",
                        "Kore": "es-MX-DaliaNeural",
                        "Leda": "es-ES-ElviraNeural",
                        "Zephyr": "es-US-AlonsoNeural",
                        "Charon": "es-MX-JorgeNeural",
                        "Puck": "es-ES-AlvaroNeural",
                        "Fenrir": "es-AR-TomasNeural",
                        "Orus": "es-CL-LorenzoNeural"
                    }
                    voice_code = voices.get(cfg.min_voice, "es-US-PalomaNeural")

                    import edge_tts
                    communicate = edge_tts.Communicate(clean_text, voice_code, rate=rate)
                    await communicate.save(temp_path)

                    def _play_and_wait():
                        try:
                            import soundfile as sf
                            data, fs = sf.read(temp_path)
                            rms_multiplier = 25
                            block_size = 480
                            with sd.OutputStream(
                                samplerate=fs,
                                channels=len(data.shape) if len(data.shape) > 1 else 1,
                                dtype="float32",
                                blocksize=block_size
                            ) as stream:
                                idx = 0
                                while idx < len(data) and self._is_speaking and not self._stop_requested.is_set():
                                    chunk = data[idx: idx + block_size]
                                    try:
                                        rms = float(np.sqrt(np.mean(chunk ** 2)))
                                        self.ui.set_audio_level(min(1.0, rms * rms_multiplier))
                                    except Exception:
                                        pass
                                    stream.write(chunk.astype(np.float32))
                                    idx += block_size
                        except Exception as pe:
                            print(f"[MIN] local play error: {pe}")
                        finally:
                            try:
                                os.remove(temp_path)
                            except:
                                pass

                    await asyncio.to_thread(_play_and_wait)
                except Exception as e:
                    print(f"[MIN] TTS local error: {e}")
                finally:
                    self.set_speaking(False)
        else:
            # Proveedor local/no-Gemini utiliza Kokoro
            if self._is_speaking:
                self.stop_playback()
                for _ in range(20):
                    if not self._is_speaking:
                        break
                    await asyncio.sleep(0.05)

            async with self._play_lock:
                self.start_stream()
                self.feed_token(text)
                self.end_stream()
                if self._playback_task:
                    try:
                        await self._playback_task
                    except Exception as e:
                        print(f"[TTS] speak_local streaming await failed: {e}")

    def speak(self, text: str):
        """Dynamic text speaking function exposed to tools."""
        if not text:
            return
        clean = _clean_tts_text(text)
        if not clean:
            print(f"[MIN] TTS: skipped (think/no-content)")
            return
        print(f"[MIN] speak command: {clean[:100]}")

        if self._is_speaking:
            print(f"[MIN] TTS: skipped (already speaking)")
            return

        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
        if self._loop:
            future = asyncio.run_coroutine_threadsafe(self.speak_local(clean), self._loop)
            try:
                future.result(timeout=20)
            except Exception as e:
                print(f"[MIN] TTS speak error: {e}")

    def speak_error(self, tool_name: str, error: str):
        msg = f"Señor, ocurrió un error en la herramienta {tool_name}."
        self.speak(msg)
