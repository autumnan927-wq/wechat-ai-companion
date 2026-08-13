from typing import Any

import httpx


class DeepSeekClientError(RuntimeError):
    """Raised when the DeepSeek chat API fails."""


class DeepSeekClient:
    def __init__(self, settings: Any) -> None:
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url.rstrip("/")
        self._model = settings.deepseek_model
        self._temperature = settings.deepseek_temperature
        self._timeout = settings.deepseek_timeout

    async def chat(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": self._temperature,
                    "stream": False,
                },
            )
        if response.status_code != 200:
            raise DeepSeekClientError(
                f"DeepSeek 请求失败({response.status_code}): {response.text[:300]}"
            )
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekClientError(f"DeepSeek 返回格式异常: {data}") from exc
