import time
from typing import Any

import httpx


class WeChatClientError(RuntimeError):
    """Raised when a WeChat API call fails."""


class WeChatClient:
    def __init__(self, settings: Any) -> None:
        self._app_id = settings.wechat_app_id.strip()
        self._app_secret = settings.wechat_app_secret.strip()
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at - 300:
            return self._access_token

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": self._app_id,
                    "secret": self._app_secret,
                },
            )
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise WeChatClientError(f"获取 access_token 失败: {data}")
        self._access_token = access_token
        self._token_expires_at = now + int(data.get("expires_in", 7200))
        return access_token

    async def download_media(self, media_id: str) -> bytes:
        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://api.weixin.qq.com/cgi-bin/media/get",
                params={"access_token": token, "media_id": media_id},
            )
        if "application/json" in response.headers.get("content-type", ""):
            raise WeChatClientError(f"下载媒体失败: {response.text}")
        return response.content

    async def upload_voice(self, audio_bytes: bytes) -> str:
        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.weixin.qq.com/cgi-bin/media/upload",
                params={"access_token": token, "type": "voice"},
                files={"media": ("voice.amr", audio_bytes, "audio/amr")},
            )
        data = response.json()
        media_id = data.get("media_id")
        if not media_id:
            raise WeChatClientError(f"上传语音失败: {data}")
        return media_id

    async def send_customer_text(self, to_user: str, content: str) -> None:
        await self._send_custom_message(
            to_user,
            {"msgtype": "text", "text": {"content": content}},
        )

    async def send_customer_voice(self, to_user: str, media_id: str) -> None:
        await self._send_custom_message(
            to_user,
            {"msgtype": "voice", "voice": {"media_id": media_id}},
        )

    async def _send_custom_message(self, to_user: str, payload: dict[str, Any]) -> None:
        token = await self.get_access_token()
        body = {"touser": to_user, **payload}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.weixin.qq.com/cgi-bin/message/custom/send",
                params={"access_token": token},
                json=body,
            )
        data = response.json()
        if data.get("errcode", 0) != 0:
            raise WeChatClientError(f"发送客服消息失败: {data}")
