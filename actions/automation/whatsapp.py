# -*- coding: utf-8 -*-
import time
import urllib.parse
import json
import os
import ctypes
from pathlib import Path

# Try to import pyautogui, if not available we will gracefully fail/log
try:
    import pyautogui
except ImportError:
    pyautogui = None

BASE_DIR = Path(__file__).resolve().parent.parent
CONTACTS_FILE = BASE_DIR / "config" / "whatsapp_contacts.json"

def load_contacts() -> dict:
    if CONTACTS_FILE.exists():
        try:
            return json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_contacts(contacts: dict):
    try:
        CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONTACTS_FILE.write_text(json.dumps(contacts, indent=4, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[WhatsApp] Error saving contacts: {e}")

def copy_image_to_clipboard(image_path: Path) -> bool:
    """Copia una imagen al portapapeles de Windows usando la API nativa de ctypes."""
    if not image_path.exists():
        return False
    try:
        from PIL import Image
        import io
        
        # Convert PIL image to clipboard format (DIB)
        image = Image.open(image_path)
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # Offset 14 is the BMP file header
        output.close()
        
        # Windows clipboard API calls
        ctypes.windll.user32.OpenClipboard(None)
        ctypes.windll.user32.EmptyClipboard()
        # CF_DIB = 8
        ctypes.windll.user32.SetClipboardData(8, ctypes.windll.kernel32.GlobalAlloc(0x0002, len(data)))
        h_clip_mem = ctypes.windll.user32.GetClipboardData(8)
        p_clip_mem = ctypes.windll.kernel32.GlobalLock(h_clip_mem)
        ctypes.cdll.msvcrt.memcpy(p_clip_mem, data, len(data))
        ctypes.windll.kernel32.GlobalUnlock(h_clip_mem)
        ctypes.windll.user32.CloseClipboard()
        return True
    except Exception as e:
        print(f"[WhatsApp] Error copying image to clipboard: {e}")
        return False

def copy_file_to_clipboard(file_path: Path) -> bool:
    """Copia un archivo al portapapeles de Windows (HDROP format) para poder pegarlo directamente."""
    if not file_path.exists():
        return False
    try:
        # Define structures for Windows Clipboard
        class DROPFILES(ctypes.Structure):
            _fields_ = [
                ("pFiles", ctypes.c_uint32),
                ("pt", ctypes.c_void_p),
                ("fNC", ctypes.c_bool),
                ("fWide", ctypes.c_bool)
            ]
        
        # Get absolute double-null terminated unicode path
        abs_path = str(file_path.resolve())
        path_bytes = (abs_path + "\0\0").encode('utf-16le')
        
        # Structure allocation
        dropfiles = DROPFILES()
        dropfiles.pFiles = ctypes.sizeof(DROPFILES)
        dropfiles.fWide = True
        
        total_data = bytes(dropfiles) + path_bytes
        
        ctypes.windll.user32.OpenClipboard(None)
        ctypes.windll.user32.EmptyClipboard()
        
        # CF_HDROP = 15
        h_global = ctypes.windll.kernel32.GlobalAlloc(0x0002, len(total_data))
        p_global = ctypes.windll.kernel32.GlobalLock(h_global)
        ctypes.cdll.msvcrt.memcpy(p_global, total_data, len(total_data))
        ctypes.windll.kernel32.GlobalUnlock(h_global)
        
        ctypes.windll.user32.SetClipboardData(15, h_global)
        ctypes.windll.user32.CloseClipboard()
        return True
    except Exception as e:
        print(f"[WhatsApp] Error copying file to clipboard: {e}")
        return False

def whatsapp(parameters: dict, player=None) -> str:
    """
    Control de WhatsApp mediante la aplicación de escritorio nativa de Windows (o Web como fallback).
    Soporta mensajería instantánea, envío de imágenes/archivos y automatización de llamadas.
    """
    action = parameters.get("action", "").lower()
    receiver = parameters.get("receiver", "")
    message = parameters.get("message", "")
    image_path = parameters.get("image_path", "")
    file_path = parameters.get("file_path", "")
    caption = parameters.get("caption", "")
    name = parameters.get("name", "")
    phone_param = parameters.get("phone", "")

    contacts = load_contacts()

    # Normalización de nombres de acciones
    if action in ["send_text", "send"]:
        action = "send"
    elif action in ["send_image", "send_img"]:
        action = "send_image"
    elif action in ["send_file", "upload_file"]:
        action = "send_file"
    elif action in ["call", "call_voice", "voice_call"]:
        action = "call_voice"
    elif action in ["video_call", "call_video"]:
        action = "call_video"

    # --- 1. GESTIÓN DE CONTACTOS ---
    if action == "add_contact":
        contact_name = name or receiver
        contact_phone = phone_param
        if not contact_name or not contact_phone:
            return "Error: Se requiere el nombre ('name') y el teléfono ('phone') para guardar el contacto."
        contact_phone = "".join(filter(str.isdigit, contact_phone))
        contacts[contact_name.lower()] = {
            "name": contact_name,
            "phone": contact_phone
        }
        save_contacts(contacts)
        return f"Contacto '{contact_name}' guardado exitosamente con teléfono: {contact_phone}."

    elif action == "delete_contact":
        contact_name = name or receiver
        if not contact_name:
            return "Error: Para eliminar un contacto se requiere el nombre ('name')."
        if contact_name.lower() in contacts:
            del contacts[contact_name.lower()]
            save_contacts(contacts)
            return f"Contacto '{contact_name}' eliminado de la base de datos de MIN."
        return f"No se encontró ningún contacto con el nombre '{contact_name}'."

    elif action == "list_contacts":
        if not contacts:
            return "No tienes contactos guardados en la base de datos de MIN."
        res = "Contactos guardados en MIN:\n"
        for k, v in contacts.items():
            res += f"• {v['name']}: {v['phone']}\n"
        return res

    # --- 2. AUTOMATIZACIÓN DE ACCIONES EN WHATSAPP ESCRITORIO ---
    if not pyautogui:
        return "Error: PyAutoGUI no está disponible. No se puede automatizar la interfaz de WhatsApp."

    # Intentar obtener el teléfono del destinatario
    phone = ""
    contact_name = ""
    if receiver:
        cleaned_receiver = "".join(c for c in receiver if c.isdigit() or c == '+')
        digit_count = sum(c.isdigit() for c in cleaned_receiver)
        if digit_count >= 8:
            phone = cleaned_receiver.replace("+", "")
        else:
            match = contacts.get(receiver.lower())
            if match:
                phone = match["phone"]
                contact_name = match["name"]
            else:
                for k, v in contacts.items():
                    if receiver.lower() in k or k in receiver.lower():
                        phone = v["phone"]
                        contact_name = v["name"]
                        break

    target_desc = contact_name if contact_name else (receiver or "contacto")

    if action in ["send", "send_image", "send_file"]:
        # Abrir chat directamente si tenemos teléfono
        if phone:
            encoded_msg = urllib.parse.quote(message)
            uri = f"whatsapp://send?phone={phone}&text={encoded_msg}"
            if player:
                player.write_log(f"💬 Abriendo canal de chat nativo con {target_desc}...")
            os.startfile(uri)
            # Dar tiempo a que cargue y enfoque
            time.sleep(3.5)
        else:
            # Abrir app general y buscar por nombre
            if player:
                player.write_log(f"💬 Abriendo WhatsApp Desktop para buscar a '{target_desc}'...")
            os.startfile("whatsapp://")
            time.sleep(3.5)
            # Buscar contacto usando atajo universal de búsqueda
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.write(receiver, interval=0.01)
            time.sleep(2.0)
            pyautogui.press('down')
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(1.0)
            if message:
                pyautogui.write(message, interval=0.01)
                time.sleep(0.5)

        # Enviar archivo si aplica
        if action == "send_file" and file_path:
            fp = Path(file_path)
            if not fp.exists():
                return f"Mensaje escrito, pero no se encontró el archivo en: {file_path}"
            if copy_file_to_clipboard(fp):
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(2.0)
                if caption:
                    pyautogui.write(caption, interval=0.01)
                    time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1.0)
                return f"Archivo '{fp.name}' enviado a '{target_desc}' exitosamente."
            else:
                return f"Error al copiar el archivo '{fp.name}' al portapapeles."

        # Enviar imagen si aplica
        elif action == "send_image" and image_path:
            ip = Path(image_path)
            if not ip.exists():
                return f"Mensaje escrito, pero no se encontró la imagen en: {image_path}"
            if copy_image_to_clipboard(ip):
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(2.0)
                if caption:
                    pyautogui.write(caption, interval=0.01)
                    time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(1.0)
                return f"Imagen '{ip.name}' enviada a '{target_desc}' exitosamente."
            else:
                return f"Error al copiar la imagen '{ip.name}' al portapapeles."

        # Enviar mensaje de texto
        pyautogui.press('enter')
        return f"Mensaje enviado exitosamente a '{target_desc}' vía WhatsApp Desktop."

    elif action in ["call_voice", "call_video"]:
        # Abrir chat primero
        if phone:
            os.startfile(f"whatsapp://send?phone={phone}")
            time.sleep(3.5)
        else:
            os.startfile("whatsapp://")
            time.sleep(3.5)
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.write(receiver, interval=0.01)
            time.sleep(2.0)
            pyautogui.press('down')
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(1.0)

        # Usar atajos de llamada nativos de la aplicación de Windows
        if action == "call_voice":
            if player:
                player.write_log(f"📞 Iniciando llamada de voz con {target_desc}...")
            # En WhatsApp Desktop para Windows, Ctrl+Shift+C inicia llamada de voz
            pyautogui.hotkey('ctrl', 'shift', 'c')
            return f"Iniciando llamada de voz a '{target_desc}' vía WhatsApp Desktop."
        else:
            if player:
                player.write_log(f"📹 Iniciando videollamada con {target_desc}...")
            # En WhatsApp Desktop para Windows, Ctrl+Shift+V inicia videollamada
            pyautogui.hotkey('ctrl', 'shift', 'v')
            return f"Iniciando videollamada a '{target_desc}' vía WhatsApp Desktop."

    else:
        # Abrir por defecto
        os.startfile("whatsapp://")
        return f"Abriendo WhatsApp Desktop para el usuario."
