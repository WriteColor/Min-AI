# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
import time

def print_banner():
    cyan = "\033[36m"
    green = "\033[32m"
    yellow = "\033[33m"
    red = "\033[31m"
    reset = "\033[0m"
    
    # Activar colores ANSI en Windows
    os.system("") 
    
    print(f"{cyan}======================================================================={reset}")
    print(f"{cyan}      __  ___   ____   _    __  ____   _____                           {reset}")
    print(f"{cyan}     / / /   | / __ \ / /  / / / __ \ / ___/                           {reset}")
    print(f"{cyan} __  / / / /| |/ /_/ // /  / / / /_/ / \\__ \\                            {reset}")
    print(f"{cyan}/ /_/ / / ___ // _, _// /__/ /  / _, _/ ___/ /                            {reset}")
    print(f"{cyan}\\____/ /_/  |_|/_/ |_|/____/_/  /_/ |_|/____/                             {reset}")
    print("                                                                       ")
    print(f"{green}                  SISTEMA DE INSTALACIÓN INTELIGENTE                   {reset}")
    print(f"{cyan}======================================================================={reset}")
    print()

def main():
    print_banner()
    print("Este asistente preparará a JARVIS para funcionar de forma óptima.")
    print()
    print(" [1] Comenzar instalación limpia (Recomendado)")
    print(" [2] Salir")
    print()
    
    try:
        opt = input("Selecciona una opción (1-2): ").strip()
    except (KeyboardInterrupt, EOFError):
        opt = "2"
        
    if opt != "1":
        print("\nSaliendo del instalador...")
        time.sleep(1.5)
        sys.exit(0)
        
    # FASE 1: Verificación de requisitos
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 1/4] - Verificando requisitos del sistema...\033[0m")
    print()
    
    print(f"[OK] Python detectado: {sys.version.split()[0]}")
    
    # Limpieza de residuos antiguos
    print("\033[33m[INFO] Limpiando archivos temporales viejos y cachés...\033[0m")
    
    basura = ["build", "dist"]
    for folder in basura:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception:
                pass
                
    archivos_basura = ["jarvis.log", "JARVIS_Beta_Installer.exe"]
    for f in os.listdir("."):
        if f.endswith(".spec") or f in archivos_basura:
            try:
                os.remove(f)
            except Exception:
                pass
                
    print("\033[32m[OK] Limpieza de residuos completada.\033[0m")
    time.sleep(1)
    
    # FASE 2: Entorno Virtual
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 2/4] - Configurando Entorno Virtual (.venv)...\033[0m")
    print()
    
    if not os.path.exists(".venv"):
        print("\033[33m[INFO] Creando un entorno virtual de Python limpio...\033[0m")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print("\033[32m[OK] Entorno virtual creado exitosamente.\033[0m")
        except Exception as e:
            print(f"\033[31m[ERROR] No se pudo crear el entorno virtual: {e}\033[0m")
            input("Presiona Enter para salir...")
            sys.exit(1)
    else:
        print("\033[32m[OK] Entorno virtual existente detectado.\033[0m")
        
    time.sleep(1)
    
    # FASE 3: Instalación de dependencias
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 3/4] - Instalando dependencias de JARVIS...\033[0m")
    print()
    print("Esto puede tomar unos minutos dependiendo de tu conexión a Internet.")
    print("Instalando requerimientos de forma segura...")
    print()
    
    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = "python" # Fallback
        
    try:
        # Upgrade pip
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        # Install requirements
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("\033[32m\n[OK] Todas las dependencias se instalaron correctamente.\033[0m")
    except Exception as e:
        print(f"\033[31m\n[ERROR] Ocurrió un error al instalar dependencias: {e}\033[0m")
        input("Presiona Enter para salir...")
        sys.exit(1)
        
    time.sleep(1)
    
    # FASE 4: Acceso directo
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 4/4] - Creación de Accesos Directos...\033[0m")
    print()
    print("Creando acceso directo en tu Escritorio para un inicio rápido...")
    print()
    
    try:
        current_dir = os.getcwd()
        icon_path = os.path.join(current_dir, "assets", "jarvis_icono.ico")
        target_vbs = os.path.join(current_dir, "Iniciar JARVIS Beta.vbs")
        
        # Usar PowerShell de forma nativa desde Python sin lidiar con escapes de comillas
        ps_cmd = (
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut(([System.Environment]::GetFolderPath('Desktop')+'\\JARVIS AI.lnk'));"
            f"$s.TargetPath='{target_vbs}';"
            f"$s.WorkingDirectory='{current_dir}';"
            f"$s.IconLocation='{icon_path}';"
            f"$s.Description='Lanzador de JARVIS AI';"
            f"$s.Save()"
        )
        
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        print("\033[32m[OK] Acceso directo 'JARVIS AI' creado en el Escritorio.\033[0m")
    except Exception as e:
        print(f"\033[33m[ADVERTENCIA] No se pudo crear el acceso directo de forma automática: {e}\033[0m")
        
    time.sleep(1)
    
    # Pantalla Final
    os.system("cls")
    print_banner()
    print("\033[32m=======================================================================")
    print("     ¡INSTALACIÓN Y CONFIGURACIÓN COMPLETADA CON ÉXITO!")
    print("=======================================================================\033[0m")
    print()
    print("JARVIS está listo para servirte.")
    print("Al iniciar el sistema por primera vez se te solicitarán tus API Keys")
    print("para Gemini y OpenRouter automáticamente de forma visual.")
    print()
    print(" [1] Iniciar JARVIS ahora mismo")
    print(" [2] Salir")
    print()
    
    try:
        launch_opt = input("Selecciona una opción (1-2): ").strip()
    except (KeyboardInterrupt, EOFError):
        launch_opt = "2"
        
    if launch_opt == "1":
        print("Iniciando JARVIS...")
        try:
            # Ejecutar el VBS silencioso
            os.startfile("Iniciar JARVIS Beta.vbs")
        except Exception:
            # Fallback si no está asociado
            subprocess.Popen(["wscript.exe", "Iniciar JARVIS Beta.vbs"])
            
    print("\nGracias por usar el instalador de JARVIS AI.")
    time.sleep(2)

if __name__ == "__main__":
    main()
