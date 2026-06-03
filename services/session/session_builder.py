"""services/session_builder.py — Build Gemini LiveConnectConfig"""

from datetime import datetime
from google.genai import types

from memory.memory_manager import load_memory, format_memory_for_prompt
from core.tool_schemas import TOOL_DECLARATIONS
from services._core.helpers import _load_tz, _BA_TZ, _load_system_prompt


class SessionBuilder:
    @staticmethod
    def build_config() -> types.LiveConnectConfig:
        from core.config_manager import get_config

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        _load_tz()
        now      = datetime.now(_BA_TZ)
        time_str = now.strftime("%A, %d %B %Y \u2014 %I:%M:%S %p")
        utc_off  = now.strftime("%z")
        tz_name  = str(_BA_TZ)
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Timezone: {tz_name} (UTC{utc_off})\n"
            f"The current Unix timestamp is: {int(now.timestamp())}\n"
            f"Use this information to calculate exact times for reminders, scheduling, and answering time-related questions.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        cfg = get_config()
        _voice_name = cfg.min_voice or "Aoede"
        # Map configured voice to Gemini Live supported voices (Aoede, Charon, Fenrir, Kore, Puck)
        # to ensure gender and tone consistency between local TTS and Gemini.
        gemini_voice_map = {
            "Aoede": "Aoede",
            "Kore": "Kore",
            "Leda": "Kore",      # Leda is female, maps to Kore (female)
            "Zephyr": "Charon",  # Zephyr is male, maps to Charon (male)
            "Charon": "Charon",
            "Puck": "Puck",
            "Fenrir": "Fenrir",
            "Orus": "Fenrir"     # Orus is male, maps to Fenrir (male)
        }
        gemini_voice = gemini_voice_map.get(_voice_name, "Aoede")
        _speech_cfg = None
        try:
            _speech_cfg = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=gemini_voice
                    )
                )
            )
        except Exception:
            _speech_cfg = None

        cfg_kwargs: dict = dict(
            response_modalities=[cfg.voice_preference or "AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
        )
        if _speech_cfg:
            cfg_kwargs["speech_config"] = _speech_cfg

        try:
            cfg_kwargs["output_audio_config"] = types.OutputAudioConfig(
                audio_encoding="LINEAR16",
                speaking_rate=cfg.speech_rate or 1.0,
            )
        except Exception:
            pass

        try:
            cfg_kwargs["temperature"] = 0.2
        except Exception:
            pass

        _vad_applied = False
        try:
            cfg_kwargs["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity="START_SENSITIVITY_HIGH",
                    end_of_speech_sensitivity="END_SENSITIVITY_HIGH",
                    prefix_padding_ms=60,
                    silence_duration_ms=350,
                )
            )
            _vad_applied = True
            print("[MIN] VAD config aplicado (typed)")
        except Exception:
            pass

        if not _vad_applied:
            try:
                cfg_kwargs["realtime_input_config"] = {
                    "automatic_activity_detection": {
                        "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                        "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                        "prefix_padding_ms": 100,
                        "silence_duration_ms": 500,
                    }
                }
                print("[MIN] VAD config aplicado (dict)")
            except Exception:
                print("[MIN] VAD config no aplicado")

        try:
            cfg_kwargs["context_window_compression"] = types.ContextWindowCompressionConfig(
                trigger_tokens=12000,
                sliding_window=types.SlidingWindow(target_tokens=6000),
            )
        except Exception:
            pass

        try:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:
            pass

        return types.LiveConnectConfig(**cfg_kwargs)
