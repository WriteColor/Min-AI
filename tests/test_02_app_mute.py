"""
Test 02: Mute/Unmute de aplicaciones
==========================
Prueba la capacidad de silenciar aplicaciones específicas.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from actions.system.computer_settings import set_app_mute, get_app_mute_state


async def test_app_mute():
    print("=" * 60)
    print("TEST 02: Mute de aplicaciones")
    print("=" * 60)

    # Aplicaciones comunes para probar
    test_apps = [
        "chrome.exe",
        "firefox.exe",
        "spotify.exe",
        "code.exe",
    ]

    for app in test_apps:
        print(f"\n[1] Probando mute de: {app}")
        try:
            # Obtener estado actual
            state_before = await get_app_mute_state(app)
            print(f"    Estado actual: {'muteado' if state_before else 'sonando'}")

            # Toggle mute
            new_state = await set_app_mute(app, not state_before)
            print(f"    Nuevo estado: {'muteado' if new_state else 'sonando'}")

            # Verificar cambio
            verify_state = await get_app_mute_state(app)
            if verify_state == new_state:
                print(f"    ✓ Verificación exitosa")
            else:
                print(f"    ✗ Falló verificación")

        except Exception as e:
            print(f"    ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("RESULTADO: Test completado")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_app_mute())
