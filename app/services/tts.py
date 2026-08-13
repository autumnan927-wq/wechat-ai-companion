import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import edge_tts


class TTSError(RuntimeError):
    """Raised when text-to-speech or audio conversion fails."""


async def synthesize_mp3(settings: Any, text: str) -> bytes:
    communicate = edge_tts.Communicate(
        text=text,
        voice=settings.tts_voice,
        rate=settings.tts_rate,
        pitch=settings.tts_pitch,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "reply.mp3"
        try:
            await communicate.save(str(output_path))
        except Exception as exc:
            raise TTSError(f"edge-tts 合成失败: {exc}") from exc
        return output_path.read_bytes()


def _find_ffmpeg(settings: Any) -> str:
    configured = getattr(settings, "ffmpeg_path", "") or ""
    if configured:
        resolved = shutil.which(configured)
        if resolved:
            return resolved
        configured_path = Path(configured)
        if configured_path.is_file():
            return str(configured_path)

    resolved = shutil.which("ffmpeg")
    if resolved:
        return resolved

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        links_path = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
        if links_path.is_file():
            return str(links_path)
        packages_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if packages_root.exists():
            for candidate in packages_root.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
                return str(candidate)

    raise TTSError("未找到 ffmpeg，请安装 ffmpeg，或设置 FFMPEG_PATH 指向 ffmpeg.exe")


def convert_mp3_to_amr(settings: Any, mp3_bytes: bytes) -> bytes:
    ffmpeg = _find_ffmpeg(settings)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "reply.mp3"
        output_path = Path(temp_dir) / "reply.amr"
        input_path.write_bytes(mp3_bytes)

        command = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "8000",
            "-ac",
            "1",
            "-c:a",
            "libopencore_amrnb",
            "-b:a",
            "12.2k",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, check=False)
        if result.returncode != 0:
            raise TTSError(f"MP3 转 AMR 失败: {result.stderr.decode(errors='ignore')[-500:]}")
        return output_path.read_bytes()
