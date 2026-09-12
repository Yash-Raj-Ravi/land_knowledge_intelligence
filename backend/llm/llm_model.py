from typing import Optional
from langchain_ollama import ChatOllama
from backend.config import LLM_MODEL, OLLAMA_BASE_URL

class LLMModel:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or LLM_MODEL
        self.model = ChatOllama(
            model=self.model_name,
            base_url=OLLAMA_BASE_URL,
            temperature=0
        )

    def generate(self, prompt: str) -> str:
        try:
            response = self.model.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"LLM generation failed: {e}")
            return '{"answer": "Unable to contact local LLM server (Ollama connection error).", "citations": [], "evidence_coverage": "INSUFFICIENT"}'
