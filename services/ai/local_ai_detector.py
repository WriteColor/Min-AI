"""
services/local_ai_detector.py — Dynamic Local AI Model Detection
==============================================================
Automatically detects the actual model available on local AI servers
(Ollama, LM Studio, Jan AI) and updates config.

Problem: OpenAI-compatible /models endpoint returns template/bogus models.
Solution: Use provider-specific endpoints to get actually downloaded models.

Supported:
  - Ollama: GET /api/tags → returns actually pulled models
  - LM Studio: GET /v1/models → returns loaded model(s)
  - Jan AI (Nitros): GET /v1/models → similar to OpenAI
"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LocalModelInfo:
    id: str
    name: str
    provider: str
    context_window: Optional[int] = None
    loaded: bool = True


class LocalAIDetector:
    """
    Detects actually available models from local AI servers.
    Unlike /models endpoint which returns template data, these endpoints
    return what the user has actually downloaded/loaded.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def detect_ollama_models(self) -> List[LocalModelInfo]:
        """
        Ollama: GET /api/tags returns list of pulled models.
        Example: {"models": [{"name": "llama3.1:latest", ...}, ...]}
        """
        models = []
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for m in data.get("models", []):
                name = m.get("name", "")
                if ":" not in name:
                    name = f"{name}:latest"

                model_id = name.split(":")[0].replace("-", "_").lower()

                models.append(LocalModelInfo(
                    id=model_id,
                    name=name,
                    provider="ollama",
                    loaded=True
                ))

        except Exception as e:
            print(f"[LocalAIDetector] Ollama detection failed: {e}")

        return models

    def detect_lm_studio_models(self) -> List[LocalModelInfo]:
        """
        LM Studio: GET /v1/models returns currently loaded model(s).
        Example: {"data": [{"id": "model-id", "object": "model", ...}], ...}
        """
        models = []
        try:
            url = f"{self.base_url}/v1/models"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for m in data.get("data", []):
                model_id = m.get("id", "")
                if model_id:
                    models.append(LocalModelInfo(
                        id=model_id.replace("/", "_").lower(),
                        name=model_id,
                        provider="lm_studio",
                        loaded=True
                    ))

        except Exception as e:
            print(f"[LocalAIDetector] LM Studio detection failed: {e}")

        return models

    def detect_all(self) -> List[LocalModelInfo]:
        """
        Try all detection methods and combine results.
        Returns only models from servers that respond.
        """
        all_models = []

        ollama_models = self.detect_ollama_models()
        if ollama_models:
            all_models.extend(ollama_models)

        lm_models = self.detect_lm_studio_models()
        if lm_models:
            all_models.extend(lm_models)

        return all_models

    def get_default_model(self) -> Optional[LocalModelInfo]:
        """
        Returns the first/default loaded model or None.
        Priority: Ollama first (most common), then LM Studio.
        """
        models = self.detect_all()
        if not models:
            return None
        return models[0]


def detect_local_models(base_url: str = "http://localhost:11434") -> List[LocalModelInfo]:
    """Convenience function to detect local models."""
    detector = LocalAIDetector(base_url=base_url)
    return detector.detect_all()


def get_default_local_model(base_url: str = "http://localhost:11434") -> Optional[LocalModelInfo]:
    """Convenience function to get default local model."""
    detector = LocalAIDetector(base_url=base_url)
    return detector.get_default_model()
