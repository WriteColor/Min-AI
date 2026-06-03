"""services/stability_monitor.py — GC and optional RAM monitor (no auto-kill)"""

import asyncio
import gc
import os


class StabilityMonitor:
    def __init__(self, ui):
        self.ui = ui

    async def run(self):
        """Monitorea periódicamente el uso de memoria y ejecuta GC.

        No mata el proceso automáticamente. Solo registra warnings.
        El usuario decide qué hacer con la info de memoria.
        """
        while True:
            await asyncio.sleep(300)
            gc.collect()
            try:
                import psutil
                proc = psutil.Process(os.getpid())
                mem_mb = proc.memory_info().rss / 1024 / 1024
                # Solo loguear — no matar
                if mem_mb > 2000:
                    print(f"[Stability] Memoria en uso: {mem_mb:.1f} MB — GC ejecutada.")
            except Exception as e:
                print(f"[Stability] Error en monitor: {e}")
