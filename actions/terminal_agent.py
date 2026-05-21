import subprocess

def terminal_agent(parameters: dict, player=None) -> str:
    """
    Ejecuta comandos en la terminal de Windows.
    """
    command = parameters.get("command", "")
    if not command:
        return "No se proporcionó ningún comando para ejecutar."
        
    try:
        # Ejecutamos el comando en PowerShell
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60, # 1 minuto máximo
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            if output:
                # Si la salida es muy larga, la acortamos
                if len(output) > 1000:
                    output = output[:1000] + "\n...[Salida truncada]"
                return f"Comando ejecutado exitosamente:\n{output}"
            else:
                return "Comando ejecutado exitosamente sin salida."
        else:
            return f"Error ejecutando comando (Código {result.returncode}):\n{error}\n{output}"
            
    except subprocess.TimeoutExpired:
        return "Error: El comando tardó demasiado tiempo en ejecutarse y fue abortado."
    except Exception as e:
        return f"Excepción fatal ejecutando terminal: {str(e)}"
