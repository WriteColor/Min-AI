# -*- coding: utf-8 -*-
"""system_monitor.py — Advanced system hardware metrics gatherer."""
import psutil
import time
import subprocess
import sys

def get_cpu_temp() -> str:
    """Intenta consultar la temperatura del CPU vía WMI utilizando PowerShell (evita instalar dependencias extra)."""
    if sys.platform != "win32":
        # En sistemas Linux/Mac, psutil podría tener soporte directo
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        return f"{entry.current}°C"
        except Exception:
            pass
        return "N/A"
        
    try:
        # Comando PowerShell para obtener temperatura de la zona térmica (convertido de décimas de Kelvin a Celsius)
        cmd = "powershell -NoProfile -ExecutionPolicy Bypass -Command \"(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature).CurrentTemperature\""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            # CurrentTemperature viene en décimas de Kelvin, ej: 3000 = 300K = 26.85°C
            raw_temp = float(result.stdout.strip())
            celsius = (raw_temp / 10.0) - 273.15
            return f"{celsius:.1f}°C"
    except Exception:
        pass
    return "No disponible (requiere permisos de Admin o soporte de hardware)"

def get_network_speeds(interval=0.2) -> tuple[float, float]:
    """Calcula las velocidades actuales de subida/bajada de red midiendo el delta de bytes transmitidos."""
    try:
        io1 = psutil.net_io_counters()
        time.sleep(interval)
        io2 = psutil.net_io_counters()
        
        bytes_sent = io2.bytes_sent - io1.bytes_sent
        bytes_recv = io2.bytes_recv - io1.bytes_recv
        
        # Convertir a MB/s
        speed_sent = (bytes_sent / interval) / (1024 * 1024)
        speed_recv = (bytes_recv / interval) / (1024 * 1024)
        return speed_sent, speed_recv
    except Exception:
        return 0.0, 0.0

def get_top_processes(limit=5) -> list[str]:
    """Obtiene la lista de los procesos que consumen más CPU y memoria actualmente."""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Obtener porcentaje de CPU (puede dar 0 si no se consulta con intervalo, pero da idea de carga acumulada)
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Ordenar por uso de CPU y memoria
        processes = sorted(processes, key=lambda p: (p['cpu_percent'] or 0.0) + (p['memory_percent'] or 0.0), reverse=True)
        
        top_list = []
        for p in processes[:limit]:
            top_list.append(f"{p['name']} (PID: {p['pid']}) - CPU: {p['cpu_percent'] or 0.0:.1f}% | RAM: {p['memory_percent'] or 0.0:.1f}%")
        return top_list
    except Exception as e:
        return [f"Error al obtener procesos: {e}"]

def system_monitor(parameters: dict = None, player=None) -> str:
    """
    Recopila métricas detalladas del estado del hardware en tiempo real:
    Uso de CPU (por núcleo), RAM (disponible/total), Almacenamiento, Red (MB/s), Procesos y Temperatura.
    """
    try:
        # CPU
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
        cpu_cores_str = ", ".join(f"C{i}:{val}%" for i, val in enumerate(cpu_cores[:8])) # Limitar a primeros 8 núcleos
        if len(cpu_cores) > 8:
            cpu_cores_str += f" (+{len(cpu_cores)-8} núcleos)"
            
        # RAM
        ram_info = psutil.virtual_memory()
        ram_percent = ram_info.percent
        ram_used_gb = ram_info.used / (1024**3)
        ram_total_gb = ram_info.total / (1024**3)
        ram_free_gb = ram_info.available / (1024**3)

        # Almacenamiento (Disco Principal)
        try:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            disk_str = f"Disco C: {disk_percent}% ({disk_used_gb:.1f}GB usados de {disk_total_gb:.1f}GB)"
        except Exception:
            disk_str = "Almacenamiento: N/A"

        # Red
        net_up, net_down = get_network_speeds()

        # Temperatura del CPU
        cpu_temp = get_cpu_temp()

        # Batería
        battery_msg = "N/A"
        try:
            battery = psutil.sensors_battery()
            if battery:
                plugged = "Cargando" if battery.power_plugged else "Batería"
                battery_msg = f"{battery.percent}% ({plugged})"
        except Exception:
            pass

        # Procesos principales
        top_procs = get_top_processes(5)
        top_procs_str = "\n".join(f"  - {p}" for p in top_procs)

        report_lines = [
            "--- DIAGNÓSTICO DE HARDWARE DE MIN ---",
            f"CPU: {cpu_total}% [{cpu_cores_str}]",
            f"Temperatura CPU: {cpu_temp}",
            f"RAM: {ram_percent}% ({ram_used_gb:.2f} GB usado / {ram_total_gb:.2f} GB total, {ram_free_gb:.2f} GB disponible)",
            disk_str,
            f"Red Actual: Bajada {net_down:.2f} MB/s | Subida {net_up:.2f} MB/s",
            f"Energía/Batería: {battery_msg}",
            "Procesos de Mayor Consumo:",
            top_procs_str
        ]

        report = "\n".join(report_lines)
        if player:
            player.write_log(f"💻 Diagnóstico de sistema recopilado.")
        return report
    except Exception as e:
        return f"Error al recuperar métricas detalladas del sistema: {e}"
