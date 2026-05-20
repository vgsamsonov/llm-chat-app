from llama_cpp import Llama
from typing import AsyncGenerator
import os
from app.config import get_settings

settings = get_settings()

class LLMService:
    def __init__(self):
        self.model = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        model_path = settings.LLM_MODEL_PATH
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}. Download a GGUF model first.")
        
        self.model = Llama(
            model_path=model_path,
            n_ctx=settings.LLM_MAX_TOKENS + 128,
            verbose=False
        )
        self._initialized = True

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        self.initialize()
        output = self.model(
            prompt,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            stream=True
        )
        for chunk in output:
            text = chunk["choices"][0]["text"]
            yield text

    async def generate_full(self, prompt: str) -> str:
        self.initialize()
        output = self.model(
            prompt,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            stream=False
        )
        return output["choices"][0]["text"]

llm_service = LLMService()