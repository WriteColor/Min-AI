"""
Test 08: Creación de letra de canción + Generación de canción
==========================
Prueba crear letra en español y luego generar canción a partir de ella.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, ".")

from actions.music.music_generation import generate_song_lyrics, generate_song_from_lyrics, generate_song_simple


TEST_DIR = Path("C:/React-Nextjs-Projects/Jarvis AI/tests_output/music_test")
TEST_DIR.mkdir(exist_ok=True)


async def test_lyrics_generation():
    """Test de generación de letras."""
    print("\n[1] Generando letra de canción (género: Rock Latino)...")

    prompt_rock = """Crea una letra de canción original en español.
    Género: Rock latino
    Tema: La libertad y los sueños de un joven que quiere escapar de la rutina
    Debe tener: Versos, coro, puente, estrofa final
    Estilo: Emotivo, con imágenes poéticas
    Longitud: 3-4 minutos de duración"""

    try:
        result = await generate_song_lyrics(prompt_rock)

        if result.get('success'):
            lyrics = result.get('lyrics', '')
            print(f"    ✓ Letra generada ({len(lyrics)} caracteres)")

            # Guardar letra
            lyrics_file = TEST_DIR / "letra_rock_latino.txt"
            lyrics_file.write_text(lyrics, encoding='utf-8')
            print(f"    → Guardada en: {lyrics_file.name}")

            # Mostrar preview
            print("\n    Preview de la letra:")
            print("    " + "-" * 40)
            lines = lyrics.split('\n')[:20]
            for line in lines:
                print(f"    {line}")
            if len(lyrics.split('\n')) > 20:
                print("    ... (continúa)")

            return lyrics
        else:
            print(f"    ✗ {result.get('message', 'Error')}")
            return None

    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return None


async def test_lyrics_pop():
    """Test de letra Pop."""
    print("\n[2] Generando letra Pop (tema: Amor de verano)...")

    prompt_pop = """Crea una letra original en español.
    Género: Pop latino / Reggaetón suave
    Tema: Un romance de verano que empieza de forma inesperada
    Debe tener: Versos cortos, coro pegadizo, flow moderno
    Incluir: español neutro, frases en inglés ocasionales
    Longitud: 2-3 minutos"""

    try:
        result = await generate_song_lyrics(prompt_pop)

        if result.get('success'):
            lyrics = result.get('lyrics', '')
            print(f"    ✓ Letra generada ({len(lyrics)} caracteres)")

            lyrics_file = TEST_DIR / "letra_pop_verano.txt"
            lyrics_file.write_text(lyrics, encoding='utf-8')

            # Preview
            print("\n    Preview:")
            print("    " + "-" * 40)
            lines = lyrics.split('\n')[:15]
            for line in lines:
                print(f"    {line}")

            return lyrics
        else:
            print(f"    ✗ {result.get('message', '')}")
            return None

    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return None


async def test_song_from_lyrics(lyrics: str):
    """Test de generar canción a partir de letra."""
    if not lyrics:
        print("\n[3] Saltando generación de canción (sin letra)")
        return False

    print("\n[3] Generando canción a partir de letra...")
    print("    ⚠ Esto puede tardar varios minutos...")

    try:
        result = await generate_song_from_lyrics(
            lyrics=lyrics,
            title="Mi Verano",
            genre="pop",
            output_path=str(TEST_DIR / "mi_verano.mp3")
        )

        if result.get('success'):
            song_path = result.get('path', '')
            duration = result.get('duration', 'N/A')
            print(f"    ✓ Canción generada!")
            print(f"    → Duración: {duration}")
            print(f"    → Guardada en: {song_path}")
            return True
        else:
            print(f"    ✗ {result.get('message', '')}")
            return False

    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return False


async def test_simple_song():
    """Test de generación simple de canción."""
    print("\n[4] Generando canción simple (descripción directa)...")

    description = """Canción de rock en español.
    Historia: Un trabajador cansado sueña con el océano.
    Emociones: Nostalgia, esperanza, determinación.
    Tempo: Medio, con explosión energética en el coro.
    Duración: 3 minutos."""

    try:
        result = await generate_song_simple(
            description=description,
            output_path=str(TEST_DIR / "sueno_oceanico.mp3")
        )

        if result.get('success'):
            print(f"    ✓ Canción generada!")
            print(f"    → {result.get('path', 'N/A')}")
            return True
        else:
            print(f"    ✗ {result.get('message', '')}")
            return False

    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return False


async def test_song_creation_with_prompt():
    """Test de creación directa con prompt de estilo."""
    print("\n[5] Creando canción con prompt de estilo específico...")

    prompt = """Crea una canción urbana/rap en español.
    Género: Rapconscious / Hip hop latino
    Tema: La realidad de las calles desde la perspectiva de un joven que quiere salir adelante
    Incluir: Metáforas con elementos de la naturaleza (agua, fuego, tierra)
    Estilo: Flows complejos, rimas internas
    Debe tener: Intro, 3 versos, coro melodic, outro
    Mood: Introspectivo pero con mensaje positivo"""

    try:
        result = await generate_song_from_lyrics(
            lyrics_or_description=prompt,
            title="Calle a la Esperanza",
            genre="rap",
            output_path=str(TEST_DIR / "calle_esperanza.mp3")
        )

        if result.get('success'):
            print(f"    ✓ Canción generada!")
            print(f"    → {result.get('path', 'N/A')}")
            print(f"    → Duración: {result.get('duration', 'N/A')}")
            return True
        else:
            print(f"    ✗ {result.get('message', '')}")
            return False

    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return False


async def main():
    print("=" * 60)
    print("TEST 08: Creación de letras y canciones")
    print("=" * 60)

    # Test 1: Rock Latino
    lyrics_rock = await test_lyrics_generation()

    # Test 2: Pop
    lyrics_pop = await test_lyrics_pop()

    # Test 3: Generación de canción (descomentar para probar)
    # results.append(await test_song_from_lyrics(lyrics_rock))

    # Test 4: Simple song
    result_simple = await test_simple_song()

    # Test 5: Prompt directo
    result_prompt = await test_song_creation_with_prompt()

    print("\n" + "=" * 60)
    print(f"RESULTADO: Generación de letras = {'✓' if lyrics_rock else '✗'}")
    print(f"          Generación simple = {'✓' if result_simple else '✗'}")
    print(f"          Con prompt complejo = {'✓' if result_prompt else '✗'}")
    print(f"          Output: {TEST_DIR}")
    print("=" * 60)

    return bool(lyrics_rock or lyrics_pop)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
