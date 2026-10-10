"""
AI-powered document classifier.
Supports LM Studio (OpenAI-compatible, default port 1234)
and Ollama (port 11434) — auto-detected at startup.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

# Probe order: LM Studio first, then Ollama
_BACKENDS = [
    ("lmstudio", "http://localhost:1234"),
    ("ollama",   "http://localhost:11434"),
]


class AIClassifier:
    TIMEOUT_PING = 3
    TIMEOUT_GEN  = 60
    TEXT_LIMIT   = 2000

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
        {".pdf", ".docx", ".doc", ".txt", ".md"}
    )

    # The only categories the model is allowed to return.  Anything else it
    # invents is discarded, so the destination tree can't sprout one-off
    # folders like "Leggi e normative" alongside "Rapporti".
    ALLOWED_CATEGORIES: frozenset[str] = frozenset({
        "Contratti", "Fatture", "Ricevute", "Rapporti", "Manuali",
        "Lettere", "CV", "Presentazioni", "Ricerca", "Moduli", "Altro",
    })

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url: str = base_url or ""
        self.backend: str = ""
        self.model: str = model or ""
        self.available = False
        self.refresh_status()

    # ------------------------------------------------------------------

    def refresh_status(self) -> bool:
        """Auto-detect a running backend; update and return self.available."""
        if self.base_url:
            # Explicit URL provided — just ping it
            backends = [("custom", self.base_url)]
        else:
            backends = _BACKENDS

        for name, url in backends:
            try:
                # LM Studio: GET /v1/models   |   Ollama: GET /api/tags
                probe = "/v1/models" if name in ("lmstudio", "custom") else "/api/tags"
                r = requests.get(f"{url}{probe}", timeout=self.TIMEOUT_PING)
                if r.status_code == 200:
                    self.base_url = url
                    self.backend  = name
                    if not self.model:
                        self.model = self._detect_model(name, url, r)
                    self.available = True
                    return True
            except Exception:
                continue

        self.available = False
        return False

    def classify(self, file_path: Path) -> dict | None:
        """
        Return {"category": str, "filename": str} or None on any failure.
        *filename* is snake_case without extension.
        """
        if not self.available:
            return None
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return None

        text = self._extract_text(file_path)
        if not text.strip():
            return None

        return self._validate(self._call_api(text[: self.TEXT_LIMIT]))

    @classmethod
    def _validate(cls, result: dict | None) -> dict | None:
        """Drop a category the model invented; keep the suggested filename.
        Without a category the organizer falls back to the extension map.
        """
        if not result:
            return None
        raw = str(result.get("category", "")).strip()
        canonical = next(
            (c for c in cls.ALLOWED_CATEGORIES if c.lower() == raw.lower()), None
        )
        if canonical:
            result["category"] = canonical
        else:
            result.pop("category", None)
        return result or None

    # ------------------------------------------------------------------
    # Private — API calls
    # ------------------------------------------------------------------

    def _call_api(self, text: str) -> dict | None:
        """Dispatch to the right API format based on detected backend."""
        if self.backend in ("lmstudio", "custom"):
            return self._call_openai_compat(text)
        return self._call_ollama(text)

    def _call_openai_compat(self, text: str) -> dict | None:
        """LM Studio / any OpenAI-compatible endpoint."""
        system = (
            "Sei un assistente che classifica documenti. "
            "Rispondi SEMPRE e SOLO con un oggetto JSON valido, senza altro testo."
        )
        user = (
            "Analizza il testo seguente e restituisci:\n"
            '{"category": "<categoria>", "filename": "<nome_snake_case>"}\n\n'
            "Categorie: Contratti, Fatture, Ricevute, Rapporti, Manuali, "
            "Lettere, CV, Presentazioni, Ricerca, Moduli, Altro.\n"
            "Il filename: breve, snake_case, senza estensione.\n\n"
            f"Testo:\n{text}"
        )
        payload: dict = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": 0.1,
            # Generation dominates the per-document cost, and the answer is one
            # short JSON object: ~30 tokens. Anything beyond this is latency.
            "max_tokens": 48,
        }
        if self.model:
            payload["model"] = self.model

        try:
            r = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.TIMEOUT_GEN,
            )
            if r.status_code != 200:
                return None
            raw: str = (
                r.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return self._parse_json(raw)
        except Exception:
            return None

    def _call_ollama(self, text: str) -> dict | None:
        """Ollama /api/generate endpoint."""
        prompt = (
            "Analizza il seguente testo estratto da un documento. "
            "Rispondi SOLO con un oggetto JSON valido (nient'altro):\n"
            '{"category": "<categoria>", "filename": "<nome>"}\n\n'
            "Categorie: Contratti, Fatture, Ricevute, Rapporti, Manuali, "
            "Lettere, CV, Presentazioni, Ricerca, Moduli, Altro.\n"
            "filename: breve, snake_case, senza estensione.\n\n"
            f"Testo:\n{text}"
        )
        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.TIMEOUT_GEN,
            )
            if r.status_code != 200:
                return None
            return self._parse_json(r.json().get("response", ""))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Private — helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_model(backend: str, url: str, probe_resp) -> str:
        """Pick a sensible default model name from the probe response."""
        try:
            if backend in ("lmstudio", "custom"):
                models = probe_resp.json().get("data", [])
                if models:
                    return models[0].get("id", "")
            else:
                models = probe_resp.json().get("models", [])
                if models:
                    return models[0].get("name", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        return None

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_text(self, path: Path) -> str:
        ext = path.suffix.lower()
        try:
            if ext in (".txt", ".md"):
                return path.read_text(encoding="utf-8", errors="ignore")
            if ext == ".pdf":
                return self._pdf_text(path)
            if ext in (".doc", ".docx"):
                return self._docx_text(path)
        except Exception:
            pass
        return ""

    @staticmethod
    def _pdf_text(path: Path) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return " ".join(p.extract_text() or "" for p in reader.pages[:5])
        except ImportError:
            return ""

    @staticmethod
    def _docx_text(path: Path) -> str:
        try:
            import docx
            doc = docx.Document(str(path))
            return " ".join(p.text for p in doc.paragraphs[:100])
        except ImportError:
            return ""
