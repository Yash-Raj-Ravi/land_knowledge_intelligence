from langchain_ollama import OllamaEmbeddings
from backend.config import EMBEDDING_MODEL,OLLAMA_BASE_URL

import logging
import hashlib

logger = logging.getLogger(__name__)

class EmbeddingModel:
    def __init__(self):
        try:
            self.model = OllamaEmbeddings(
                model = EMBEDDING_MODEL,
                base_url = OLLAMA_BASE_URL
            )
        except Exception:
            self.model = None

    def _fallback_embedding(self, text: str) -> list[float]:
        # Generate deterministic 1024-d pseudo-embedding from text hash
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(b / 255.0) for b in h]
        while len(vec) < 1024:
            vec.extend(vec[:1024 - len(vec)])
        return vec[:1024]

    def embed_text(self, text: str) -> list[float]:  # Query embedding
        try:
            if self.model:
                return self.model.embed_query(text)
        except Exception as e:
            logger.warning(f"Ollama embedding offline ({e}). Using deterministic fallback vector.")
        return self._fallback_embedding(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]: # Document Chunks embedding
        try:
            if self.model:
                return self.model.embed_documents(texts)
        except Exception as e:
            logger.warning(f"Ollama embedding offline ({e}). Using deterministic fallback vectors.")
        return [self._fallback_embedding(t) for t in texts]






