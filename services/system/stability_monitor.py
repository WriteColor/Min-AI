"""services/stability_monitor.py — RAM/Crash stability monitor"""

import asyncio
import gc
import os
import sys
import subprocess
from pathlib import Path


class StabilityMonitor:
    def __init__(self, ui):
        self.ui = ui

    async def run(self):
        """Monitorea periódicamente el consumo de RAM y ejecuta GC. Si supera el umbral, reinicia."""
        import psutil
        from core.config_manager import get_config

        while True:
            await asyncio.sleep(300)
            gc.collect()
            try:
                cfg = get_config()
                max_mem = float(cfg.max_memory_mb or 500.0)

                proc = psutil.Process(os.getpid())
                mem_mb = proc.memory_info().rss / 1024 / 1024
                if mem_mb > max_mem:
                    print(f"[MIN] \u26a0\ufe0f Uso de memoria ({mem_mb:.1f} MB) excedi\u00f3 el l\u00edmite ({max_mem:.1f} MB). Reiniciando preventivamente...")
                    self.ui.write_log(f"SYS: Uso de memoria elevado ({mem_mb:.1f} MB). Reiniciando preventivamente...")

                    main_py = str(Path(__file__).resolve().parent.parent / "main.py")
                    subprocess.Popen([sys.executable, main_py], creationflags=0x00000008)
                    os._exit(0)
            except Exception as e:
                print(f"[MIN] Error en monitor de estabilidad: {e}")
