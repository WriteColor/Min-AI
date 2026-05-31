"""
Test 06: Control de música (Spotify)
==========================
Prueba play, pause, next, previous, volume en Spotify.
"""

import asyncio
import sys
sys.path.insert(0, ".")

from actions.music.spotify_control import spotify_play, spotify_pause, spotify_next, spotify_previous
from actions.music.spotify_control import spotify_volume, spotify_current_song, spotify_search


async def test_spotify_basic():
    """Test de controles básicos."""
    print("\n[1] Test de controles básicos:")

    tests = [
        ("Play", spotify_play),
        ("Pause", spotify_pause),
        ("Next", spotify_next),
        ("Previous", spotify_previous),
    ]

    results = []
    for name, func in tests:
        try:
            result = await func()
            success = result.get('success', False)
            results.append(success)
            status = "✓" if success else "✗"
            print(f"    {status} {name}: {result.get('message', '')}")
        except Exception as e:
            results.append(False)
            print(f"    ✗ {name}: {e}")

    return all(results)


async def test_spotify_volume():
    """Test de control de volumen."""
    print("\n[2] Test de volumen:")

    volumes = [0, 25, 50, 75, 100]

    for vol in volumes:
        try:
            result = await spotify_volume(vol)
            success = result.get('success', False)
            status = "✓" if success else "✗"
            print(f"    {status} Volumen {vol}%: {result.get('message', '')}")
        except Exception as e:
            print(f"    ✗ Volumen {vol}%: {e}")
        await asyncio.sleep(0.5)

    return True


async def test_spotify_info():
    """Test de obtener información de canción actual."""
    print("\n[3] Info de canción actual:")

    try:
        result = await spotify_current_song()
        if result.get('success'):
            data = result.get('data', {})
            print(f"    ✓ Canción: {data.get('name', 'N/A')}")
            print(f"      Artista: {data.get('artist', 'N/A')}")
            print(f"      Álbum: {data.get('album', 'N/A')}")
            print(f"      Duración: {data.get('duration', 'N/A')}")
            return True
        else:
            print(f"    ✗ {result.get('message', 'No se pudo obtener info')}")
            return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


async def test_spotify_search():
    """Test de búsqueda."""
    print("\n[4] Búsqueda de canciones:")

    queries = [
        "Rock en español",
        "Jazz instrumental",
        "Lo-fi beats",
        "Música clásica"
    ]

    for query in queries:
        try:
            result = await spotify_search(query)
            if result.get('success'):
                results_list = result.get('results', [])
                print(f"    ✓ '{query}': {len(results_list)} resultados")
                if results_list:
                    top = results_list[0]
                    print(f"       Top: {top.get('name', 'N/A')} - {top.get('artist', 'N/A')}")
            else:
                print(f"    ✗ '{query}': {result.get('message', '')}")
        except Exception as e:
            print(f"    ✗ '{query}': {e}")
        await asyncio.sleep(0.5)

    return True


async def main():
    print("=" * 60)
    print("TEST 06: Control de música Spotify")
    print("=" * 60)

    results = []
    results.append(await test_spotify_basic())
    results.append(await test_spotify_volume())
    results.append(await test_spotify_info())
    results.append(await test_spotify_search())

    print("\n" + "=" * 60)
    print(f"RESULTADO: {sum(results)}/{len(results)} tests aprobados")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
