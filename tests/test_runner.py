"""
MIN AI - Test Suite Runner
==========================
Ejecuta todos los tests de forma secuencial o individual.

Uso:
    python test_runner.py              # Ejecutar todos los tests
    python test_runner.py --list        # Listar tests disponibles
    python test_runner.py --run 01      # Ejecutar test específico
    python test_runner.py --category music  # Ejecutar por categoría
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Tests disponibles con metadata
TESTS = {
    "01": {
        "name": "Aplicaciones/Juegos instalados",
        "file": "test_01_installed_apps.py",
        "category": "system",
        "description": "Descubre apps y juegos instalados en Windows"
    },
    "02": {
        "name": "Mute de aplicaciones",
        "file": "test_02_app_mute.py",
        "category": "system",
        "description": "Silencia aplicaciones específicas"
    },
    "03": {
        "name": "Creación de archivos extensos",
        "file": "test_03_file_creation.py",
        "category": "files",
        "description": "Crea txt, md (LaTeX), docx, xlsx, pptx"
    },
    "04": {
        "name": "Estructuras de carpetas fractales",
        "file": "test_04_fractal_folders.py",
        "category": "files",
        "description": "Crea carpetas con patrones fractales"
    },
    "05": {
        "name": "Eliminación a papelera",
        "file": "test_05_recycle_bin.py",
        "category": "files",
        "description": "Elimina archivos a papelera de reciclaje"
    },
    "06": {
        "name": "Control de música Spotify",
        "file": "test_06_music_control.py",
        "category": "music",
        "description": "Play, pause, next, volume, search"
    },
    "07": {
        "name": "Búsqueda web sin navegador",
        "file": "test_07_web_search.py",
        "category": "search",
        "description": "Busca información resumida en internet"
    },
    "08": {
        "name": "Creación de letras y canciones",
        "file": "test_08_song_creation.py",
        "category": "music",
        "description": "Genera letras y canciones en español"
    },
    "09": {
        "name": "Verificación de personalidad",
        "file": "test_09_personality.py",
        "category": "personality",
        "description": "Verifica cambio de estilo conversacional"
    },
    # Tests legacy
    "legacy": {
        "name": "Test v2 (WebSocket)",
        "file": "test_v2.py",
        "category": "legacy",
        "description": "Test de conexión WebSocket"
    },
    "simple": {
        "name": "Test simple legacy",
        "file": "test_simple.py",
        "category": "legacy",
        "description": "Tests simples heredados"
    }
}

CATEGORIES = {
    "system": ["01", "02"],
    "files": ["03", "04", "05"],
    "music": ["06", "08"],
    "search": ["07"],
    "personality": ["09"],
    "legacy": ["legacy", "simple"],
    "all": list(TESTS.keys())
}


def list_tests():
    """Lista todos los tests disponibles."""
    print("\n" + "=" * 60)
    print("MIN AI - Tests Disponibles")
    print("=" * 60)

    for test_id, info in TESTS.items():
        if test_id == "legacy":
            continue
        print(f"\n[{test_id}] {info['name']}")
        print(f"    Categoría: {info['category']}")
        print(f"    Descripción: {info['description']}")

    print("\n" + "-" * 60)
    print("CATEGORÍAS:")
    for cat, ids in CATEGORIES.items():
        if cat != "all":
            print(f"  {cat}: {', '.join(ids)}")

    print("\n" + "=" * 60)


async def run_test(test_id: str) -> bool:
    """Ejecuta un test específico."""
    if test_id not in TESTS:
        print(f"✗ Test '{test_id}' no encontrado")
        return False

    test_info = TESTS[test_id]
    test_file = Path(__file__).parent / test_info["file"]

    if not test_file.exists():
        print(f"✗ Archivo no encontrado: {test_file}")
        return False

    print(f"\n{'=' * 60}")
    print(f"Ejecutando: [{test_id}] {test_info['name']}")
    print(f"Categoría: {test_info['category']}")
    print(f"{'=' * 60}")

    try:
        # Importar y ejecutar
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"test_{test_id}", test_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Asumimos que el test tiene una función main() o se ejecuta directamente
        if hasattr(module, 'main'):
            result = await module.main()
        else:
            print("✗ El test no tiene función main()")
            result = False

        return result

    except Exception as e:
        print(f"✗ Error ejecutando test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_category(category: str) -> dict:
    """Ejecuta todos los tests de una categoría."""
    if category not in CATEGORIES:
        print(f"✗ Categoría '{category}' no encontrada")
        return {}

    print(f"\n{'#' * 60}")
    print(f"# Ejecutando categoría: {category.upper()}")
    print(f"{'#' * 60}")

    results = {}
    for test_id in CATEGORIES[category]:
        results[test_id] = await run_test(test_id)
        await asyncio.sleep(1)  # Pausa entre tests

    return results


async def run_all() -> dict:
    """Ejecuta todos los tests."""
    print(f"\n{'#' * 60}")
    print(f"# EJECUTANDO TODOS LOS TESTS")
    print(f"{'#' * 60}")

    results = {}
    for test_id in TESTS.keys():
        if test_id == "legacy":
            continue  # Saltar legacy por defecto
        results[test_id] = await run_test(test_id)
        await asyncio.sleep(2)

    return results


def print_summary(results: dict):
    """Imprime resumen de resultados."""
    print(f"\n{'=' * 60}")
    print("RESUMEN DE RESULTADOS")
    print(f"{'=' * 60}")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_id, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        test_name = TESTS.get(test_id, {}).get("name", test_id)
        print(f"  [{test_id}] {status} - {test_name}")

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {passed}/{total} tests aprobados")

    if passed == total:
        print("✓ ¡Todos los tests pasaron!")
    else:
        print(f"✗ {total - passed} tests fallaron")

    print(f"{'=' * 60}")


async def main():
    parser = argparse.ArgumentParser(description="MIN AI Test Runner")
    parser.add_argument("--list", action="store_true", help="Listar tests disponibles")
    parser.add_argument("--run", metavar="ID", help="Ejecutar test específico (ej: 01)")
    parser.add_argument("--category", metavar="CAT", help="Ejecutar categoría (system/files/music/search/personality)")
    parser.add_argument("--all", action="store_true", help="Ejecutar todos los tests")

    args = parser.parse_args()

    if args.list:
        list_tests()
        return

    if args.run:
        result = await run_test(args.run)
        sys.exit(0 if result else 1)

    if args.category:
        results = await run_category(args.category)
        print_summary(results)
        sys.exit(0 if all(results.values()) else 1)

    if args.all:
        results = await run_all()
        print_summary(results)
        sys.exit(0 if all(results.values()) else 1)

    # Sin argumentos: mostrar help
    parser.print_help()
    print("\nEjemplos:")
    print("  python test_runner.py --list              # Ver tests")
    print("  python test_runner.py --run 01            # Ejecutar test 01")
    print("  python test_runner.py --category music    # Todos de música")
    print("  python test_runner.py --all               # Ejecutar todos")


if __name__ == "__main__":
    asyncio.run(main())
