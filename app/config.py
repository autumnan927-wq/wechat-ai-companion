from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    app_name: str = "wechat-ai-companion"
    debug: bool = False

    wechat_token: str = ""
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_encoding_aes_key: str = ""
    wechat_encrypt_mode: bool = False

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.8
    deepseek_timeout: float = 4.5

    companion_name: str = "小伴"
    persona: str = (
        "你是一个温柔、幽默、善解人意的 AI 聊天伴侣，名字是 {name}。"
        "你记得用户之前说过的重要内容，会用自然口语化的中文回复。"
        "回复要简洁、有温度，像真正的朋友一样聊天，不要使用机械的列表。"
    )
    max_history_messages: int = 16
    style_examples: str = ""
    memory_file: str = "data/memory.json"

    reply_mode: str = "voice"
    tts_enabled: bool = True
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"
    voice_max_chars: int = 280
    ffmpeg_path: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def persona_prompt(self) -> str:
        return self.persona.format(name=self.companion_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
