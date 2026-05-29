"""
Security
========
Funciones de seguridad para el sistema MIN AI.

Proporciona:
- Encriptación/Decriptación
- Hashing seguro
- Generación de tokens
- Sanitización de inputs
- Rate limiting
"""

from typing import Any, Optional, Tuple
import hashlib
import hmac
import secrets
import base64
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import time


@dataclass
class EncryptedData:
    """Datos encriptados."""
    ciphertext: bytes
    nonce: bytes
    tag: Optional[bytes] = None


class SecurityUtils:
    """
    Utilidades de seguridad.
    
    Uso:
        # Hash
        hashed = SecurityUtils.hash_password('password123')
        
        # Verify
        if SecurityUtils.verify_password('password123', hashed):
            print("Access granted")
        
        # Encrypt
        encrypted = SecurityUtils.encrypt(plaintext, key)
        
        # Token
        token = SecurityUtils.generate_token(32)
    """
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        """
        Hash de contraseña usando Argon2 o PBKDF2.
        
        Args:
            password: Contraseña en texto plano
            salt: Salt (generado si no se provee)
        
        Returns:
            Hash en formato: algorithm$salt$hash
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        try:
            import argon2
            hash_result = argon2.PasswordHasher().hash(password)
            return hash_result
        except ImportError:
            import hashlib
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100000
            )
            return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verificar contraseña contra hash.
        
        Args:
            password: Contraseña a verificar
            password_hash: Hash almacenado
        
        Returns:
            True si la contraseña coincide
        """
        try:
            import argon2
            ph = argon2.PasswordHasher()
            ph.verify(password_hash, password)
            return True
        except ImportError:
            if password_hash.startswith('pbkdf2_sha256$'):
                parts = password_hash.split('$')
                if len(parts) != 3:
                    return False
                salt = base64.b64decode(parts[1])
                stored_hash = base64.b64decode(parts[2])
                
                key = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    salt,
                    100000
                )
                return hmac.compare_digest(key, stored_hash)
        except Exception:
            return False
        
        return False
    
    @staticmethod
    def encrypt(plaintext: str, key: bytes) -> EncryptedData:
        """
        Encriptar texto usando AES-GCM.
        
        Args:
            plaintext: Texto a encriptar
            key: Clave de encriptación (32 bytes para AES-256)
        
        Returns:
            EncryptedData con ciphertext, nonce, y tag
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            if len(key) != 32:
                key = hashlib.sha256(key).digest()
            
            nonce = secrets.token_bytes(12)
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
            
            return EncryptedData(
                ciphertext=ciphertext[:-16],
                nonce=nonce,
                tag=ciphertext[-16:]
            )
        except ImportError:
            raise ImportError("cryptography library not installed. Run: pip install cryptography")
    
    @staticmethod
    def decrypt(encrypted: EncryptedData, key: bytes) -> str:
        """
        Desencriptar texto usando AES-GCM.
        
        Args:
            encrypted: EncryptedData con ciphertext, nonce, y tag
            key: Clave de encriptación
        
        Returns:
            Texto plano original
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            if len(key) != 32:
                key = hashlib.sha256(key).digest()
            
            aesgcm = AESGCM(key)
            ciphertext_with_tag = encrypted.ciphertext + (encrypted.tag or b'')
            plaintext = aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, None)
            
            return plaintext.decode('utf-8')
        except ImportError:
            raise ImportError("cryptography library not installed. Run: pip install cryptography")
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generar token seguro random.
        
        Args:
            length: Longitud en bytes (el string será el doble en hex)
        
        Returns:
            Token en hex
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_api_key(prefix: str = "min") -> str:
        """
        Generar API key con prefijo.
        
        Args:
            prefix: Prefijo para la key
        
        Returns:
            API key formateada: prefix_randomkey
        """
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"
    
    @staticmethod
    def sanitize_filename(filename: str, replacement: str = "_") -> str:
        """
        Sanitizar nombre de archivo para evitar path traversal.
        
        Args:
            filename: Nombre original
            replacement: Caracter de reemplazo para caracteres inválidos
        
        Returns:
            Nombre sanitizado
        """
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', replacement, filename)
        filename = filename.strip('. ')
        
        if not filename:
            filename = "unnamed"
        
        filename = filename[:255]
        
        dangerous_patterns = ['..', '~/', '^/', '%00']
        for pattern in dangerous_patterns:
            filename = filename.replace(pattern, replacement)
        
        return filename
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """
        Sanitizar input para queries SQL (usar siempre parameterized queries!).
        
        Args:
            value: Valor a sanitizar
        
        Returns:
            Valor sanitizado
        """
        if not value:
            return ""
        
        value = str(value)
        value = value.replace("'", "''")
        value = value.replace(";", "")
        value = value.replace("--", "")
        value = value.replace("/*", "")
        value = value.replace("*/", "")
        
        dangerous = ['UNION', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'EXEC', 'EXECUTE']
        for keyword in dangerous:
            if keyword in value.upper():
                value = value.upper().replace(keyword, '')
        
        return value
    
    @staticmethod
    def sanitize_html(value: str) -> str:
        """
        Sanitizar HTML para prevenir XSS.
        
        Args:
            value: Valor a sanitizar
        
        Returns:
            HTML seguro
        """
        if not value:
            return ""
        
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'style']
        dangerous_attrs = ['onerror', 'onclick', 'onload', 'onmouseover', 'onfocus', 'onblur']
        
        for tag in dangerous_tags:
            value = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', value, flags=re.IGNORECASE | re.DOTALL)
            value = re.sub(f'<{tag}[^>]*/?>', '', value, flags=re.IGNORECASE)
        
        for attr in dangerous_attrs:
            value = re.sub(f'{attr}\\s*=\\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
            value = re.sub(f'{attr}\\s*=', '', value, flags=re.IGNORECASE)
        
        return value
    
    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """
        Comparación en tiempo constante para evitar timing attacks.
        
        Args:
            a: Primer string
            b: Segundo string
        
        Returns:
            True si son iguales
        """
        return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


class RateLimiter:
    """
    Rate limiter con sliding window.
    
    Uso:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        if limiter.is_allowed("user_123"):
            process_request()
        else:
            reject_request()
    """
    
    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Verificar si request está permitido.
        
        Args:
            identifier: Identificador único (user_id, IP, etc)
        
        Returns:
            True si está permitido
        """
        with self._lock:
            now = time.time()
            cutoff = now - self._window_seconds
            
            if identifier not in self._requests:
                self._requests[identifier] = []
            
            self._requests[identifier] = [
                t for t in self._requests[identifier]
                if t > cutoff
            ]
            
            if len(self._requests[identifier]) >= self._max_requests:
                return False
            
            self._requests[identifier].append(now)
            return True
    
    def get_remaining(self, identifier: str) -> int:
        """Obtener requests restantes en ventana actual."""
        with self._lock:
            if identifier not in self._requests:
                return self._max_requests
            
            now = time.time()
            cutoff = now - self._window_seconds
            
            active_requests = [
                t for t in self._requests[identifier]
                if t > cutoff
            ]
            
            return max(0, self._max_requests - len(active_requests))
    
    def reset(self, identifier: str) -> None:
        """Resetear contador para identificador."""
        with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]
    
    def clear(self) -> None:
        """Limpiar todos los contadores."""
        with self._lock:
            self._requests.clear()
