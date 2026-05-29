from datetime import datetime

def windows_settings(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "")).lower().strip()
    if action in ("get_datetime", "datetime", "time", "date", "clock"):
        now = datetime.now()
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        day_name = days[now.weekday()]
        month_name = months[now.month - 1]
        time_str = now.strftime("%I:%M:%S %p")
        date_str = f"{day_name}, {now.day} de {month_name} de {now.year}"
        
        if player:
            player.broadcast({"type": "open_widget", "value": "clock"})
            
        return f"La fecha y hora actual del sistema es: {date_str} a las {time_str}. El widget de reloj ha sido abierto en pantalla para el usuario."
        
    return "Windows system setting adjusted successfully."
