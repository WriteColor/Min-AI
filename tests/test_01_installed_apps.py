"""
Test 01: Descubrir aplicaciones/juegos instalados en Windows
==========================
Prueba la capacidad de MIN para detectar aplicaciones instaladas.
"""

import asyncio
import json
import sys
import time
sys.path.insert(0, ".")

from actions.system.windows_settings import get_installed_apps, get_installed_games


async def test_installed_apps():
    print("=" * 60)
    print("TEST 01: Aplicaciones/Juegos instalados")
    print("=" * 60)

    print("\n[1] Buscando aplicaciones instaladas...")
    apps = await get_installed_apps()
    print(f"    → {len(apps)} aplicaciones encontradas")

    if apps:
        print("\n    Primeras 10 aplicaciones:")
        for i, app in enumerate(apps[:10], 1):
            print(f"    {i}. {app.get('name', 'N/A')} - {app.get('version', 'N/A')}")

    print("\n[2] Buscando juegos instalados...")
    games = await get_installed_games()
    print(f"    → {len(games)} juegos encontrados")

    if games:
        print("\n    Lista de juegos:")
        for i, game in enumerate(games, 1):
            print(f"    {i}. {game.get('name', 'N/A')} - {game.get('install_location', 'N/A')[:50]}...")

    print("\n" + "=" * 60)
    print(f"RESULTADO: {len(apps)} apps, {len(games)} juegos")
    print("=" * 60)

    return len(apps) > 0 or len(games) > 0


if __name__ == "__main__":
    result = asyncio.run(test_installed_apps())
    sys.exit(0 if result else 1)
