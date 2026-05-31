"""
Test 04: Creación de estructura de carpetas fractales
==========================
Prueba la creación de carpetas con estructura fractal/recursiva.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, ".")

from actions.files.file_controller import create_directory, delete_to_recycle_bin


TEST_BASE = Path("C:/React-Nextjs-Projects/Jarvis AI/tests_output/fractal_test")


def generate_sierpinski_depth(parent_path: Path, depth: int, max_depth: int = 4):
    """Genera estructura tipo Sierpinski (triángulo fractal)."""
    if depth > max_depth:
        return []

    dirs_to_create = []
    current_path = parent_path / f"level_{depth}"

    if depth == 0:
        # Triángulo de Sierpinski: 3 subdirectorios
        for i in range(3):
            dirs_to_create.append(current_path / f"branch_{i}")
    else:
        # En cada nivel, crear 2 subdirectorios
        for i in range(2):
            dirs_to_create.append(current_path / f"node_{i}")

    return dirs_to_create


def generate_fibonacci_tree(parent_path: Path, depth: int, fib_prev: int = 1, fib_curr: int = 1):
    """Genera estructura tipo árbol Fibonacci."""
    if depth > 5:
        return []

    dirs_to_create = []
    current_path = parent_path / f"fib_{fib_curr}"

    # Crear directorio actual
    dirs_to_create.append(current_path)

    # Recursión: siguiente número de Fibonacci
    fib_next = fib_prev + fib_curr
    left = generate_fibonacci_tree(current_path, depth + 1, fib_curr, fib_next)
    right = generate_fibonacci_tree(current_path, depth + 1, fib_curr, fib_next)

    dirs_to_create.extend(left)
    dirs_to_create.extend(right)

    return dirs_to_create


def generate_mandelbrot_grid(parent_path: Path, grid_size: int = 3, depth: int = 0):
    """Genera estructura tipo Mandelbrot (grid recursivo)."""
    if depth > 3:
        return []

    dirs_to_create = []

    for row in range(grid_size):
        for col in range(grid_size):
            current_path = parent_path / f"r{row}_c{col}"
            dirs_to_create.append(current_path)

            # Subgrid más pequeño
            if depth < 3:
                subdirs = generate_mandelbrot_grid(current_path, grid_size - 1, depth + 1)
                dirs_to_create.extend(subdirs)

    return dirs_to_create


async def create_fractal_structure(structure_type: str, generator_func, description: str):
    """Crea una estructura fractal usando una función generadora."""
    print(f"\n[+] {description}...")

    struct_path = TEST_BASE / structure_type
    try:
        # Generar estructura
        all_dirs = generator_func(struct_path.parent, 0)
        all_dirs = [struct_path] + all_dirs

        # Crear todos los directorios
        created_count = 0
        for dir_path in all_dirs:
            result = await create_directory(str(dir_path))
            if result.get('success'):
                created_count += 1

        # Contar total
        total = sum(1 for _ in struct_path.rglob("*") if _.is_dir()) + 1

        print(f"    → Estructura: {created_count} carpetas creadas")
        print(f"    → Total en disco: ~{total} carpetas")

        # Mostrar estructura (primer nivel)
        if struct_path.exists():
            print(f"    → Estructura inicial:")
            for i, item in enumerate(struct_path.iterdir()):
                if item.is_dir():
                    subcount = sum(1 for _ in item.rglob("*") if _.is_dir())
                    print(f"       📁 {item.name}/ ({subcount} subcarpetas)")

        return True
    except Exception as e:
        print(f"    → ✗ Error: {e}")
        return False


async def main():
    print("=" * 60)
    print("TEST 04: Estructuras de carpetas fractales")
    print("=" * 60)

    # Limpiar directorio de pruebas anterior
    if TEST_BASE.exists():
        import shutil
        shutil.rmtree(TEST_BASE)
    TEST_BASE.mkdir(parents=True)

    results = []

    # Sierpinski (triángulo fractal)
    results.append(await create_fractal_structure(
        "sierpinski",
        lambda p, d: generate_sierpinski_depth(p, d, 4),
        "Creando estructura Sierpinski (profundidad 4)"
    ))

    # Fibonacci tree
    results.append(await create_fractal_structure(
        "fibonacci_tree",
        lambda p, d: generate_fibonacci_tree(p, d),
        "Creando estructura Árbol Fibonacci"
    ))

    # Mandelbrot grid
    results.append(await create_fractal_structure(
        "mandelbrot_grid",
        lambda p, d: generate_mandelbrot_grid(p, 3, 0),
        "Creando estructura Grid Mandelbrot"
    ))

    print("\n" + "=" * 60)
    print(f"RESULTADO: {sum(results)}/{len(results)} estructuras creadas")
    print(f"Ubicación: {TEST_BASE}")
    print("=" * 60)

    #统计
    total_dirs = sum(1 for _ in TEST_BASE.rglob("*") if _.is_dir())
    print(f"Total de carpetas: {total_dirs}")

    return all(results)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
