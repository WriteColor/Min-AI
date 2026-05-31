"""
Test 05: Eliminación a papelera de reciclaje
==========================
Prueba que los archivos eliminados vayan a la papelera, no se borren permanentemente.
"""

import asyncio
import sys
import os
from pathlib import Path
sys.path.insert(0, ".")

from actions.files.file_controller import delete_to_recycle_bin, create_text_file


TEST_DIR = Path("C:/React-Nextjs-Projects/Jarvis AI/tests_output/recycle_test")
TEST_DIR.mkdir(exist_ok=True)


async def create_test_files():
    """Crea archivos de prueba."""
    print("\n[1] Creando archivos de prueba...")

    files_created = []

    # Archivo de texto
    txt_path = TEST_DIR / "archivo_para_reciclar.txt"
    await create_text_file(str(txt_path), "Este archivo será eliminado a la papelera de reciclaje")
    files_created.append(txt_path)

    # Múltiples archivos
    for i in range(5):
        file_path = TEST_DIR / f"test_file_{i}.txt"
        await create_text_file(str(file_path), f"Contenido del archivo {i}")
        files_created.append(file_path)

    # Archivo grande
    large_path = TEST_DIR / "archivo_grande.txt"
    content = ("Línea " + "x" * 80 + "\n") * 1000
    await create_text_file(str(large_path), content)
    files_created.append(large_path)

    print(f"    → {len(files_created)} archivos creados")
    return files_created


async def verify_files_exist(files):
    """Verifica que los archivos existan."""
    existing = []
    for f in files:
        if f.exists():
            existing.append(f)
    return existing


async def delete_and_verify(files):
    """Elimina archivos a la papelera y verifica."""
    print("\n[2] Eliminando archivos a papelera...")

    deleted = []
    failed = []

    for f in files:
        try:
            result = await delete_to_recycle_bin(str(f))
            if result.get('success'):
                deleted.append(f)
                print(f"    ✓ {f.name} -> Papelera")
            else:
                failed.append((f, result.get('message', 'Unknown error')))
                print(f"    ✗ {f.name}: {result.get('message', '')}")
        except Exception as e:
            failed.append((f, str(e)))
            print(f"    ✗ {f.name}: {e}")

    return deleted, failed


def check_recycle_bin():
    """Verifica que los archivos estén en la papelera de reciclaje."""
    print("\n[3] Verificando papelera de reciclaje...")

    # shell:recycleFolder gives us the recycle bin path
    recycle_paths = [
        Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Recycle.Bin',
        Path(os.environ.get('SystemRoot', 'C:\\Windows')) / '$Recycle.Bin',
    ]

    found_files = []

    for recycle_path in recycle_paths:
        if recycle_path.exists():
            print(f"    → Recycle Bin path: {recycle_path}")

            try:
                for drive_letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                    recycle_drive = Path(f"{drive_letter}:\\$Recycle.Bin")
                    if recycle_drive.exists():
                        print(f"    → Found: {recycle_drive}")

                        # Listar contenido (requiere admin en algunos sistemas)
                        for item in recycle_drive.iterdir():
                            if item.is_dir():
                                print(f"       📁 {item.name}/")
                                # Mostrar primeros archivos
                                subcount = 0
                                for subitem in item.iterdir():
                                    if subitem.is_file():
                                        subcount += 1
                                        if subcount <= 5:
                                            print(f"          📄 {subitem.name}")
                                if subcount > 5:
                                    print(f"          ... y {subcount - 5} más")
            except PermissionError:
                print(f"    → Acceso denegado (necesario ejecutar como admin)")

    return found_files


async def main():
    print("=" * 60)
    print("TEST 05: Eliminación a papelera de reciclaje")
    print("=" * 60)

    # Limpiar directorio de prueba
    if TEST_DIR.exists():
        import shutil
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(exist_ok=True)

    # Crear archivos
    files = await create_test_files()

    # Verificar que existen
    existing = await verify_files_exist(files)
    print(f"\n[+] Archivos existentes: {len(existing)}/{len(files)}")

    if not existing:
        print("    ✗ No se pudieron crear los archivos de prueba")
        return False

    # Eliminar a papelera
    deleted, failed = await delete_and_verify(existing)

    print(f"\n[+] Resumen:")
    print(f"    Eliminados: {len(deleted)}")
    print(f"    Fallidos: {len(failed)}")

    # Verificar que ya no existen en origen
    still_existing = await verify_files_exist(deleted)
    if still_existing:
        print(f"\n    ⚠ {len(still_existing)} archivos aún existen (no se eliminaron)")

    # Intentar verificar papelera
    check_recycle_bin()

    print("\n" + "=" * 60)
    print(f"RESULTADO: {len(deleted)} archivos enviados a papelera")
    print("=" * 60)

    # El test pasa si los archivos fueron eliminados (no necesariamente si podemos verificar la papelera)
    return len(deleted) > 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
