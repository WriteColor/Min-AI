"""services/llm.py — Generic LLM consumer for non-Gemini providers"""

import asyncio
import json
import traceback
from datetime import datetime


class LLMConsumer:
    def __init__(self, ui, tts_service, local_command_queue):
        self.ui = ui
        self.tts_service = tts_service
        self._local_command_queue = local_command_queue

    async def run(self, provider_name: str):
        """Consume comandos typed/transcribed locally, query LLM provider and speak output."""
        from core.config_manager import get_config
        from providers.base import get_provider_class, ProviderConfig
        import providers
        from services._core.helpers import _load_system_prompt, _load_tz, _BA_TZ

        while True:
            text = await self._local_command_queue.get()
            if not text:
                continue

            self.ui.set_state("THINKING")
            cfg = get_config()

            # 1. Resolve prompt context using new database memory if available, fallback to memory manager
            mem_str = ""
            try:
                from memory.service import MemoryService
                memory_service = MemoryService()
                facts = memory_service.search_memory(text, top_k=5)
                if facts:
                    mem_str = "[LONG-TERM MEMORY & USER CONTEXT]\n"
                    for val, score in facts:
                        mem_str += f"- {val}\n"

                recent = memory_service.get_recent_context(max_interactions=5)
                if recent:
                    mem_str += f"\n[RECENT SESSION]\n{recent}\n"
            except Exception as me:
                print(f"[MIN] Failed to load memory service: {me}")
                try:
                    from memory.memory_manager import load_memory, format_memory_for_prompt
                    memory = load_memory()
                    mem_str = format_memory_for_prompt(memory)
                except Exception:
                    mem_str = ""

            sys_prompt = _load_system_prompt()

            # Mix time context
            _load_tz()
            now = datetime.now(_BA_TZ)
            time_str = now.strftime("%A, %d %B %Y \u2014 %I:%M:%S %p")
            tz_name = str(_BA_TZ)
            time_ctx = (
                f"[CURRENT DATE & TIME]\n"
                f"Right now it is: {time_str}\n"
                f"Timezone: {tz_name}\n\n"
            )

            full_prompt = f"{time_ctx}{mem_str}\n{sys_prompt}\n\nUser request: {text}"

            self.ui.clear_min_response()
            self.ui.stream_min_chunk("Pensando...")

            # 2. Execute LLM call using the provider registry
            provider_class = get_provider_class(provider_name)

            # Fallback for local_openai/local
            if not provider_class:
                if provider_name == "local_openai":
                    provider_class = get_provider_class("local")

            if not provider_class:
                self.ui.clear_min_response()
                self.ui.stream_min_chunk(f"Error: El proveedor '{provider_name}' no est\u00e1 registrado.")
                self.ui.set_state("LISTENING")
                continue

            # Build ProviderConfig
            api_key = ""
            base_url = None
            model = ""

            if provider_name in ("local_openai", "local", "compatible_local_openai"):
                api_key = cfg.compatible_local_openai_api_key or "not-needed"
                base_url = cfg.compatible_local_openai_base_url
                model = cfg.compatible_local_openai_model or "mistral-7b-instruct"
            elif provider_name == "gemini":
                api_key = cfg.gemini_api_key
                model = cfg.active_model or "gemini-2.5-flash"
            elif provider_name == "openai":
                api_key = cfg.openai_api_key
                model = cfg.active_model or "gpt-4o"
            elif provider_name == "groq":
                api_key = cfg.groq_api_key if hasattr(cfg, "groq_api_key") else ""
                model = cfg.active_model or "llama-3.1-8b-instant"
            elif provider_name == "openrouter":
                api_key = cfg.openrouter_api_key
                model = cfg.openrouter_default_model or "google/gemini-2.5-flash:free"
            elif provider_name == "opencode":
                api_key = cfg.openrouter_api_key
                model = "meta-llama/llama-3.1-405b-instruct"
            elif provider_name == "minimax":
                api_key = cfg.minimax_api_key
                model = cfg.minimax_llm_model or "MiniMax-M2.7"
            elif provider_name == "ollama_cloud":
                api_key = cfg.ollama_cloud_api_key
                base_url = cfg.ollama_cloud_base_url
                model = cfg.ollama_cloud_model or "nemotron-3-super:cloud"
            elif provider_name == "nvidia_nim":
                api_key = cfg.nvidia_nim_api_key
                base_url = cfg.nvidia_nim_base_url
                model = cfg.nvidia_nim_model or "meta/llama-3.1-70b-instruct"

            prov_cfg = ProviderConfig(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=0.2,
                max_tokens=2048
            )

            try:
                # Instantiate and connect
                provider_inst = provider_class(prov_cfg)
                connected = await provider_inst.connect()
                if not connected:
                    raise RuntimeError("No se pudo conectar al proveedor.")

                self.ui.clear_min_response()

                full_resp = ""
                async for chunk in provider_inst.stream_text(full_prompt):
                    if chunk:
                        full_resp += chunk
                        self.ui.stream_min_chunk(chunk)

                # Log episodic interaction in database if available
                try:
                    from memory.service import MemoryService
                    MemoryService().log_user_message(text)
                    MemoryService().log_min_response(full_resp)
                except Exception:
                    pass

                # Speak response
                await self.tts_service.speak_local(full_resp)

            except Exception as e:
                self.ui.clear_min_response()
                self.ui.stream_min_chunk(f"Error al conectar con {provider_name}: {e}")
                print(f"[MIN] Generic LLM error for {provider_name}: {e}")
                traceback.print_exc()

            self.ui.set_state("LISTENING")
