import time
import urllib.parse
import webbrowser
import pyautogui

def whatsapp(parameters: dict, player=None) -> str:
    """
    Control básico de WhatsApp Web usando automatización de teclado y navegador.
    """
    action = parameters.get("action", "")
    
    if action in ["read_unread", "read_chat"]:
        # Abrir WhatsApp Web para que el usuario pueda leer
        webbrowser.open("https://web.whatsapp.com")
        return "Abriendo WhatsApp Web. Debido al cifrado de extremo a extremo, los mensajes deben leerse directamente en la pantalla."
        
    elif action == "send_text":
        phone = parameters.get("phone", "")
        message = parameters.get("message", "")
        contact_name = parameters.get("contact_name", "")
        
        target = phone if phone else contact_name
        if not target or not message:
            return "Faltan datos (número o mensaje) para enviar el WhatsApp."
            
        # Formatear la URL de WhatsApp
        encoded_msg = urllib.parse.quote(message)
        if phone:
            # Limpiar numero
            phone = "".join(filter(str.isdigit, phone))
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
        else:
            # Buscar contacto
            url = f"https://web.whatsapp.com/send?text={encoded_msg}"
            
        webbrowser.open(url)
        
        # Esperar a que cargue la web (puede variar según la PC, 12 segundos suele ser seguro)
        time.sleep(12)
        
        if not phone and contact_name:
            # Si solo se dio el nombre, hay que buscarlo
            # Presionar Tab un par de veces para llegar al buscador, o usar el atajo Ctrl+Alt+/ (buscar)
            pyautogui.hotkey('ctrl', 'alt', '/')
            time.sleep(1)
            pyautogui.write(contact_name)
            time.sleep(2)
            pyautogui.press('enter')
            time.sleep(2)
            
        # Presionar Enter para enviar el mensaje
        pyautogui.press('enter')
        
        return f"Mensaje enviado a {target} vía WhatsApp Web."
        
    else:
        webbrowser.open("https://web.whatsapp.com")
        return f"Ejecutando acción {action} de forma manual en WhatsApp Web."
