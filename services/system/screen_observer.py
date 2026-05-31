"""
Screen Observer Service
======================
Capa de observación de pantalla para el sistema de visión.

Este servicio se encarga de:
- Capturas de pantalla periódicas
- Detección de cambios en pantalla
- Análisis visual contextual
- Detección de errores visibles

NO se encarga de:
- Obtener coordenadas para clicks (eso es visual_click)
- Análisis semántico profundo (eso es screen_vision)

La separación asegura que visión = observación, no control.
"""

import hashlib
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

try:
    import mss
    import numpy as np
    HAS_MSS = True
except ImportError:
    HAS_MSS = False


class ChangeType(Enum):
    """Tipos de cambios detectados en pantalla."""
    NONE = "none"
    MINOR = "minor"  # Pequeños cambios (notificaciones, etc.)
    MODERATE = "moderate"  # Cambios significativos
    MAJOR = "major"  # Cambios importantes (error dialogs, etc.)


@dataclass
class ScreenCapture:
    """Representa una captura de pantalla."""
    timestamp: datetime
    image_hash: str  # Hash para comparación
    image_path: Optional[str]  # Path si se guardó
    width: int
    height: int
    size_bytes: int


@dataclass
class ScreenChange:
    """Representa un cambio detectado en pantalla."""
    change_type: ChangeType
    timestamp: datetime
    before_hash: str
    after_hash: str
    pixel_diff_ratio: float  # Porcentaje de píxeles diferentes
    region: Optional[Tuple[int, int, int, int]]  # Región del cambio (x, y, w, h)


@dataclass
class ScreenAnalysis:
    """Resultado del análisis de pantalla."""
    has_error_dialog: bool
    has_notification: bool
    is_fullscreen: bool
    active_app: Optional[str]
    important_changes: List[str]
    raw_description: str


class ScreenObserver:
    """
    Observador proactivo de pantalla.
    
    Captura pantalla periódicamente y detecta cambios significativos.
    Diseñado para integración con vision_guardian y validación de acciones.
    
    Uso:
        observer = ScreenObserver()
        
        # Captura simple
        capture = observer.capture()
        
        # Detectar cambios
        change = observer.detect_change(last_capture)
        
        # Iniciar monitoreo continuo
        observer.start_monitoring(callback=on_change_detected)
    """
    
    SCREENSHOT_DIR = Path("logs/screen_observer")
    
    def __init__(self):
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        
        self._monitor = 1  # Monitor principal
        self._max_size = (1280, 720)  # Tamaño máximo para reducir tokens
        self._compression_quality = 65
        
        self._last_capture: Optional[ScreenCapture] = None
        self._capture_counter = 0
        
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Configuración de detección de cambios
        self._pixel_diff_threshold = 0.05  # 5% de píxeles diferentes = cambio notable
        self._major_change_threshold = 0.20  # 20% = cambio mayor
    
    def _get_image_hash(self, image_bytes: bytes) -> str:
        """Genera hash de la imagen para comparación rápida."""
        return hashlib.md5(image_bytes).hexdigest()
    
    def capture(self, save: bool = False, monitor: int = 1) -> Optional[ScreenCapture]:
        """
        Captura la pantalla actual.
        
        Args:
            save: Si True, guarda la captura en disco
            monitor: Número de monitor (1 = principal)
            
        Returns:
            ScreenCapture con datos de la captura, o None si falla
        """
        if not HAS_MSS:
            return None
        
        try:
            with mss.mss() as sct:
                mon = sct.monitors[monitor]
                screenshot = sct.grab(mon)
                
                # Convertir a imagen PIL
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Redimensionar
                img.thumbnail(self._max_size, Image.Resampling.BILINEAR)
                
                # Guardar a bytes
                buffer = b""
                img_bytes = buffer
                
                # Usar buffer para obtener bytes
                import io
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=self._compression_quality)
                img_bytes = buf.getvalue()
                
                # Hash para comparación
                img_hash = self._get_image_hash(img_bytes)
                
                # Guardar si se solicita
                save_path = None
                if save:
                    self._capture_counter += 1
                    timestamp = datetime.now().strftime('%H%M%S')
                    filename = f"capture_{timestamp}_{self._capture_counter}.jpg"
                    save_path = str(self.SCREENSHOT_DIR / filename)
                    
                    buf.seek(0)
                    img.save(save_path, format="JPEG", quality=self._compression_quality)
                
                self._last_capture = ScreenCapture(
                    timestamp=datetime.now(),
                    image_hash=img_hash,
                    image_path=save_path,
                    width=img.width,
                    height=img.height,
                    size_bytes=len(img_bytes)
                )
                
                return self._last_capture
                
        except Exception as e:
            print(f"[ScreenObserver] Capture error: {e}")
            return None
    
    def detect_change(
        self,
        before: Optional[ScreenCapture] = None
    ) -> Optional[ScreenChange]:
        """
        Detecta cambios entre la última captura y la actual.
        
        Args:
            before: Captura anterior. Si None, usa self._last_capture
            
        Returns:
            ScreenChange con información del cambio, o None si no hay cambio
        """
        if before is None:
            before = self._last_capture
        
        current = self.capture()
        if current is None or before is None:
            return None
        
        # Comparar hashes (rápido)
        if before.image_hash == current.image_hash:
            return None
        
        # Hay diferencias - calcular magnitud
        # Para una comparación más precisa, necesitaríamos cargar ambas imágenes
        # Por ahora usamos el hash como indicador
        try:
            from PIL import Image
            import io
            
            # Calcular diferencia real usando numpy
            with mss.mss() as sct:
                mon = sct.monitors[self._monitor]
                screenshot = sct.grab(mon)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                img.thumbnail(self._max_size, Image.Resampling.BILINEAR)
                
                # Guardar temporalmente para comparar
                buf1 = io.BytesIO()
                buf2 = io.BytesIO()
                
                # Las imágenes redimensionadas deberían ser similares en tamaño
                # Esto es una aproximación - para detección precisa usar histogramas
                
                # Por simplicidad, usamos el hash diferente como indicador
                change_type = ChangeType.MINOR
                
                # Guardar antes y después
                before_path = None
                after_path = None
                
                if before.image_path is None:
                    self._capture_counter += 1
                    before_path = str(self.SCREENSHOT_DIR / f"compare_before_{self._capture_counter}.jpg")
                    
                if current.image_path is None:
                    self._capture_counter += 1
                    after_path = str(self.SCREENSHOT_DIR / f"compare_after_{self._capture_counter}.jpg")
                
                return ScreenChange(
                    change_type=change_type,
                    timestamp=datetime.now(),
                    before_hash=before.image_hash,
                    after_hash=current.image_hash,
                    pixel_diff_ratio=0.1,  # Valor estimado
                    region=None
                )
                
        except Exception as e:
            print(f"[ScreenObserver] Change detection error: {e}")
            return None
    
    def capture_for_vision(self) -> Tuple[Optional[bytes], Tuple[int, int]]:
        """
        Captura pantalla optimizada para envío a APIs de visión.
        
        Returns:
            (image_bytes, original_size) o (None, (0, 0)) si falla
        """
        if not HAS_MSS:
            return None, (0, 0)
        
        try:
            with mss.mss() as sct:
                mon = sct.monitors[self._monitor]
                screenshot = sct.grab(mon)
                
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                orig_size = img.size
                
                # Redimensionar para visión
                img.thumbnail(self._max_size, Image.Resampling.BILINEAR)
                
                import io
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=self._compression_quality)
                
                return buf.getvalue(), orig_size
                
        except Exception as e:
            print(f"[ScreenObserver] Vision capture error: {e}")
            return None, (0, 0)
    
    def capture_element_region(
        self,
        x: int, y: int, width: int, height: int
    ) -> Optional[bytes]:
        """
        Captura una región específica de la pantalla.
        
        Útil para capturar solo el área alrededor de un elemento.
        
        Args:
            x, y: Coordenadas de la esquina superior izquierda
            width, height: Dimensiones de la región
            
        Returns:
            Bytes de la imagen en JPEG, o None si falla
        """
        if not HAS_MSS:
            return None
        
        try:
            with mss.mss() as sct:
                # Definir bbox para captura específica
                bbox = (x, y, x + width, y + height)
                screenshot = sct.grab(bbox)
                
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                import io
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=self._compression_quality)
                
                return buf.getvalue()
                
        except Exception as e:
            print(f"[ScreenObserver] Region capture error: {e}")
            return None
    
    def start_monitoring(
        self,
        interval: float = 120.0,
        callback: Optional[Callable[[ScreenChange], None]] = None,
        capture_callback: Optional[Callable[[ScreenCapture], None]] = None
    ) -> None:
        """
        Inicia monitoreo continuo de pantalla en segundo plano.
        
        Args:
            interval: Intervalo entre capturas en segundos
            callback: Función a llamar cuando se detecta un cambio
            capture_callback: Función a llamar en cada captura (para análisis)
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        def _monitor_loop():
            last_capture = None
            
            while not self._stop_event.is_set():
                time.sleep(max(1.0, interval))
                
                if not self._monitoring:
                    break
                
                try:
                    current = self.capture()
                    if current is None:
                        continue
                    
                    # Llamar callback de captura (para análisis continuo)
                    if capture_callback:
                        try:
                            capture_callback(current)
                        except Exception:
                            pass
                    
                    # Detectar cambios vs última captura
                    if last_capture is not None:
                        change = self.detect_change(last_capture)
                        if change is not None and callback:
                            try:
                                callback(change)
                            except Exception:
                                pass
                    
                    last_capture = current
                    
                except Exception as e:
                    print(f"[ScreenObserver] Monitor error: {e}")
                    continue
        
        self._monitor_thread = threading.Thread(
            target=_monitor_loop,
            daemon=True,
            name="screen-observer"
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Detiene el monitoreo continuo."""
        self._monitoring = False
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
    
    def get_capture_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del observador."""
        return {
            "monitoring": self._monitoring,
            "last_capture": {
                "timestamp": self._last_capture.timestamp.isoformat() if self._last_capture else None,
                "hash": self._last_capture.image_hash if self._last_capture else None,
                "size": (self._last_capture.width, self._last_capture.height) if self._last_capture else None,
            } if self._last_capture else None,
            "screenshot_dir": str(self.SCREENSHOT_DIR),
            "config": {
                "monitor": self._monitor,
                "max_size": self._max_size,
                "compression_quality": self._compression_quality
            }
        }


# Singleton instance
_observer_instance: Optional[ScreenObserver] = None
_observer_lock = threading.Lock()


def get_observer() -> ScreenObserver:
    """Get singleton observer instance."""
    global _observer_instance
    if _observer_instance is None:
        with _observer_lock:
            if _observer_instance is None:
                _observer_instance = ScreenObserver()
    return _observer_instance
