"""
MIN AI - Test Suite para Windows Service
=========================================
Script de pruebas para verificar funcionalidad del módulo Windows.

Uso:
    python tests/test_windows_service.py

Autor: MIN AI Team
Fecha: 2025-05-28
"""

import sys
import time
import traceback
from typing import Tuple, Optional, List, Any

# Agregar el directorio raíz al path para imports
sys.path.insert(0, r'C:\React-Nextjs-Projects\Jarvis AI')

from services.windows_api import get_windows_service, WindowsService, WindowInfo, ProcessInfo


class TestResult:
    """Resultado de una prueba."""
    
    def __init__(self, name: str, success: bool, message: str = "", data: Any = None):
        self.name = name
        self.success = success
        self.message = message
        self.data = data
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    def __str__(self):
        status = "✓ PASS" if self.success else "✗ FAIL"
        return f"[{self.timestamp}] {self.name}: {status} - {self.message}"


class WindowsServiceTester:
    """Clase para ejecutar pruebas del WindowsService."""
    
    def __init__(self):
        self.service = get_windows_service()
        self.results: List[TestResult] = []
    
    def run_test(self, name: str, test_func, *args, **kwargs) -> TestResult:
        """Ejecuta una prueba individual."""
        try:
            result = test_func(*args, **kwargs)
            if isinstance(result, TestResult):
                self.results.append(result)
                return result
            else:
                # Asumir éxito si no hay excepción pero no hay TestResult
                test_result = TestResult(name=name, success=True, message="Ejecutado sin errores")
                self.results.append(test_result)
                return test_result
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            test_result = TestResult(name=name, success=False, message=error_msg, data=traceback.format_exc())
            self.results.append(test_result)
            return test_result
    
    # ── Pruebas de Window Management ─────────────────────────────────────────
    
    def test_get_all_windows(self) -> TestResult:
        """Prueba: Obtener todas las ventanas visibles."""
        name = "get_all_windows()"
        try:
            windows = self.service.get_all_windows()
            if isinstance(windows, list):
                return TestResult(
                    name=name,
                    success=True,
                    message=f"Encontradas {len(windows)} ventanas",
                    data={"count": len(windows), "sample": [w.title[:50] for w in windows[:5]]}
                )
            else:
                return TestResult(name=name, success=False, message=f"Tipo de retorno inesperado: {type(windows)}")
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_find_window_by_title(self) -> TestResult:
        """Prueba: Buscar ventana por título."""
        name = "find_window_by_title()"
        try:
            # Buscar el Bloc de notas como prueba
            # Nota: el parametro es 'exact' no 'partial'
            window = self.service.find_window_by_title("Notepad")
            if window is None:
                return TestResult(name=name, success=True, message="No se encontro Bloc de notas (esperado si no esta abierto)")
            elif isinstance(window, WindowInfo):
                return TestResult(name=name, success=True, message=f"Ventana encontrada: {window.title}", data={"hwnd": window.hwnd})
            else:
                return TestResult(name=name, success=False, message=f"Tipo de retorno inesperado: {type(window)}")
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_get_window_info(self) -> TestResult:
        """Prueba: Obtener información de una ventana por HWND."""
        name = "get_window_info()"
        try:
            windows = self.service.get_all_windows()
            if windows:
                test_hwnd = windows[0].hwnd
                info = self.service.get_window_info(test_hwnd)
                if info and isinstance(info, WindowInfo):
                    return TestResult(
                        name=name,
                        success=True,
                        message=f"Info obtenida para HWND {test_hwnd}: {info.title[:30]}",
                        data={"title": info.title, "state": info.state.value if hasattr(info.state, 'value') else str(info.state)}
                    )
                else:
                    return TestResult(name=name, success=False, message="No se pudo obtener info de ventana")
            else:
                return TestResult(name=name, success=False, message="No hay ventanas para probar")
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_find_running_app(self) -> TestResult:
        """Prueba: Detectar si una app está corriendo."""
        name = "find_running_app()"
        try:
            # Probar con chrome, edge, o processador
            result = self.service.find_running_app("explorer")
            if result is None:
                return TestResult(name=name, success=True, message="Explorer no está corriendo (o no tiene ventana)", data={"found": False})
            elif isinstance(result, WindowInfo) or hasattr(result, 'hwnd'):
                return TestResult(name=name, success=True, message=f"Explorer encontrado: {getattr(result, 'title', 'N/A')}", data={"found": True})
            else:
                return TestResult(name=name, success=False, message=f"Tipo de retorno inesperado: {type(result)}")
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_get_processes(self) -> TestResult:
        """Prueba: Obtener lista de procesos."""
        name = "get_processes()"
        try:
            processes = self.service.get_processes(refresh=True)
            if isinstance(processes, list):
                # Contarpython.exe y otros procesos del sistema
                py_procs = [p for p in processes if 'python' in p.name.lower()]
                return TestResult(
                    name=name,
                    success=True,
                    message=f"Obtenidos {len(processes)} procesos, {len(py_procs)} son Python",
                    data={"total": len(processes), "python_count": len(py_procs)}
                )
            else:
                return TestResult(name=name, success=False, message=f"Tipo de retorno inesperado: {type(processes)}")
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_volume_control(self) -> TestResult:
        """Prueba: Control de volumen del sistema."""
        name = "Volume Control"
        try:
            # Obtener volumen actual
            current = self.service.get_volume()
            if not isinstance(current, int):
                return TestResult(name=name, success=False, message=f"Tipo de retorno inesperado: {type(current)}")
            
            # Intentar establecer volumen al 50%
            success = self.service.set_volume(50)
            time.sleep(0.5)
            verify = self.service.get_volume()
            
            return TestResult(
                name=name,
                success=success and isinstance(verify, int),
                message=f"Volumen ajustado: anterior={current}%, nuevo={verify}%",
                data={"set_result": success, "verify_value": verify}
            )
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_capture_screen(self) -> TestResult:
        """Prueba: Captura de pantalla."""
        name = "capture_screen()"
        try:
            screenshot = self.service.capture_screen(monitor=0)
            if screenshot is None:
                return TestResult(name=name, success=False, message="capture_screen retornó None")
            elif isinstance(screenshot, bytes):
                size_kb = len(screenshot) / 1024
                return TestResult(
                    name=name,
                    success=True,
                    message=f"Captura exitosa: {size_kb:.1f} KB",
                    data={"size_bytes": len(screenshot), "size_kb": round(size_kb, 1)}
                )
            else:
                return TestResult(name=name, success=False, message=f"Tipo de retorno inesperado: {type(screenshot)}")
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_service_initialization(self) -> TestResult:
        """Prueba: Verificar que el servicio se inicializa correctamente."""
        name = "Service Initialization"
        try:
            from services.windows_api import _windows_service
            
            if _windows_service is None:
                return TestResult(name=name, success=False, message="Singleton no inicializado")
            
            has_required_methods = all([
                hasattr(_windows_service, 'find_window_by_title'),
                hasattr(_windows_service, 'launch_app'),
                hasattr(_windows_service, 'get_processes'),
                hasattr(_windows_service, 'get_all_windows'),
            ])
            
            return TestResult(
                name=name,
                success=has_required_methods,
                message="Servicio inicializado correctamente con todos los métodos",
                data={"methods_count": sum(1 for m in dir(_windows_service) if not m.startswith('_'))}
            )
        except Exception as e:
            return TestResult(name=name, success=False, message=str(e))
    
    def test_has_pywinauto(self) -> TestResult:
        """Prueba: Verificar disponibilidad de pywinauto."""
        name = "pywinauto availability"
        from services.windows_api import HAS_PYWINAUTO, HAS_WIN32, HAS_PSUTIL
        
        return TestResult(
            name=name,
            success=HAS_WIN32,  # pywinauto es optional, win32 is required
            message=f"HAS_WIN32={HAS_WIN32}, HAS_PSUTIL={HAS_PSUTIL}, HAS_PYWINAUTO={HAS_PYWINAUTO}",
            data={"HAS_WIN32": HAS_WIN32, "HAS_PSUTIL": HAS_PSUTIL, "HAS_PYWINAUTO": HAS_PYWINAUTO}
        )
    
    # ── Ejecutor de Pruebas ─────────────────────────────────────────────────
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Ejecuta todas las pruebas y retorna resumen."""
        print("=" * 60)
        print("MIN AI - Windows Service Test Suite")
        print("=" * 60)
        print()
        
        # Pruebas básicas de inicialización
        self.run_test("Service Initialization", self.test_service_initialization)
        self.run_test("pywinauto availability", self.test_has_pywinauto)
        
        # Pruebas de Window Management
        print("\n[Window Management]")
        self.run_test("get_all_windows()", self.test_get_all_windows)
        self.run_test("find_window_by_title()", self.test_find_window_by_title)
        self.run_test("get_window_info()", self.test_get_window_info)
        
        # Pruebas de App Lifecycle
        print("\n[App Lifecycle]")
        self.run_test("find_running_app()", self.test_find_running_app)
        
        # Pruebas de Process Management
        print("\n[Process Management]")
        self.run_test("get_processes()", self.test_get_processes)
        
        # Pruebas de System Control
        print("\n[System Control]")
        self.run_test("Volume Control", self.test_volume_control)
        
        # Pruebas de Screenshot
        print("\n[Screenshot]")
        self.run_test("capture_screen()", self.test_capture_screen)
        
        # Resumen
        print("\n" + "=" * 60)
        print("RESUMEN DE PRUEBAS")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)
        total = len(self.results)
        
        print(f"\nTotal: {total} | PASS: {passed} | FAIL: {failed}")
        print()
        
        for result in self.results:
            status = "PASS" if result.success else "FAIL"
            print(f"  [{status}] {result.name}: {result.message}")
        
        print()
        
        # Detalles de fallos
        if failed > 0:
            print("-" * 60)
            print("FAILURE DETAILS")
            print("-" * 60)
            for result in self.results:
                if not result.success:
                    print(f"\nFAIL: {result.name}")
                    print(f"  Message: {result.message}")
                    if result.data:
                        print(f"  Traceback: {str(result.data)[:200]}...")
        
        return passed, failed


def main():
    """Función principal."""
    tester = WindowsServiceTester()
    passed, failed = tester.run_all_tests()
    
    # Guardar resultados en DEBUG_LOG
    try:
        with open(r"C:\React-Nextjs-Projects\Jarvis AI\DEBUG_LOG.md", "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n")
            f.write(f"## Sesión de Pruebas: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Resultado:** {passed} pasadas, {failed} fallidas\n\n")
            f.write("### Detalle de Pruebas:\n\n")
            for r in tester.results:
                status = "✓ PASS" if r.success else "✗ FAIL"
                f.write(f"- **{r.name}**: {status} - {r.message}\n")
    except Exception as e:
        print(f"Warning: No se pudo actualizar DEBUG_LOG.md: {e}")
    
    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()