import json
import logging
from typing import AsyncGenerator, List, Dict
import httpx
from app.config import settings

logger = logging.getLogger("uvicorn")

class NvidiaClient:
    def __init__(self):
        self.api_key = settings.nvidia_api_key
        self.api_url = f"{settings.nvidia_api_url.rstrip('/')}/chat/completions"
        self.model = settings.nvidia_model_name

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.5, model: str = None) -> str:
        """Standard non-streaming generation"""
        if not self.api_key or self.api_key == "mock-nvidia-key":
            logger.warning("NVIDIA_API_KEY is not set or mock. Returning mock response.")
            return "This is a mock NVIDIA response. Set NVIDIA_API_KEY to see live responses."

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Error calling NVIDIA API: {e}")
                return f"Error calling NVIDIA API: {str(e)}"

    async def generate_stream(self, messages: List[Dict[str, str]], temperature: float = 0.5, model: str = None) -> AsyncGenerator[str, None]:
        """Streaming token generation yielding text chunks"""
        if not self.api_key or self.api_key == "mock-nvidia-key":
            logger.warning("NVIDIA_API_KEY is not set or mock. Mocking streaming token output.")
            mock_text = "This is a mock NVIDIA streaming response. Please configure a valid NVIDIA_API_KEY."
            for chunk in mock_text.split(" "):
                yield chunk + " "
            return

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024,
            "stream": True
        }

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=60.0
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data_json = json.loads(data_str)
                                content = data_json["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                continue
            except Exception as e:
                logger.error(f"Error in NVIDIA streaming client: {e}")
                yield f"Error in NVIDIA streaming client: {str(e)}"

nvidia_client = NvidiaClient()
