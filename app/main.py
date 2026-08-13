import asyncio
import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.services.chat import SessionStore, build_messages
from app.services.deepseek import DeepSeekClient
from app.services.tts import TTSError, convert_mp3_to_amr, synthesize_mp3
from app.wechat.client import WeChatClient, WeChatClientError
from app.wechat.crypto import (
    check_encrypted_signature,
    check_signature,
    decrypt_message,
)
from app.wechat.messages import build_text_reply, build_voice_reply, message_is_event, parse_message

logger = logging.getLogger("wechat_companion")

settings = get_settings()
app = FastAPI(title=settings.app_name)

wechat = WeChatClient(settings)
deepseek = DeepSeekClient(settings)
sessions = SessionStore(settings.max_history_messages)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/config")
async def health_config() -> dict[str, object]:
    return {
        "wechat_token": bool(settings.wechat_token),
        "wechat_app_id": bool(settings.wechat_app_id),
        "wechat_app_secret": bool(settings.wechat_app_secret),
        "deepseek_api_key": bool(settings.deepseek_api_key),
        "reply_mode": settings.reply_mode,
    }


@app.get("/wechat")
async def verify_wechat(
    signature: str = Query(default=""),
    timestamp: str = Query(default=""),
    nonce: str = Query(default=""),
    echostr: str = Query(default=""),
    msg_signature: str = Query(default=""),
) -> PlainTextResponse:
    if settings.wechat_encrypt_mode:
        if not check_encrypted_signature(
            settings.wechat_token,
            timestamp,
            nonce,
            msg_signature,
            echostr,
        ):
            raise HTTPException(status_code=403, detail="invalid signature")
        plain_echo = decrypt_message(echostr, settings.wechat_encoding_aes_key, settings.wechat_app_id)
        return PlainTextResponse(plain_echo)

    if not check_signature(settings.wechat_token, timestamp, nonce, signature):
        raise HTTPException(status_code=403, detail="invalid signature")
    return PlainTextResponse(echostr)


@app.post("/wechat")
async def receive_wechat(
    request: Request,
    background_tasks: BackgroundTasks,
    signature: str = Query(default=""),
    timestamp: str = Query(default=""),
    nonce: str = Query(default=""),
    msg_signature: str = Query(default=""),
) -> PlainTextResponse:
    body = await request.body()
    xml_text = body.decode("utf-8")

    if settings.wechat_encrypt_mode:
        raw_message = parse_message(xml_text)
        encrypted = raw_message.get("Encrypt", "")
        if not check_encrypted_signature(
            settings.wechat_token,
            timestamp,
            nonce,
            msg_signature,
            encrypted,
        ):
            raise HTTPException(status_code=403, detail="invalid signature")
        xml_text = decrypt_message(encrypted, settings.wechat_encoding_aes_key, settings.wechat_app_id)
    elif not check_signature(settings.wechat_token, timestamp, nonce, signature):
        raise HTTPException(status_code=403, detail="invalid signature")

    message = parse_message(xml_text)
    if settings.wechat_encrypt_mode:
        background_tasks.add_task(handle_message, message)
        return PlainTextResponse("success")

    reply = await handle_message_passive(message)
    return PlainTextResponse(reply or "success")


async def handle_message(message: dict[str, str]) -> None:
    user_id = message.get("FromUserName", "")
    msg_type = message.get("MsgType", "").lower()

    if not user_id:
        logger.warning("消息缺少 FromUserName: %s", message)
        return

    if message_is_event(message):
        event = message.get("Event", "").lower()
        if event == "subscribe":
            await _send_text(user_id, f"嗨，我是 {settings.companion_name}，很高兴认识你。你可以发文字，也可以发语音和我聊天。")
        return

    if msg_type == "text":
        user_text = message.get("Content", "").strip()
    elif msg_type == "voice":
        user_text = message.get("Recognition", "").strip()
        if not user_text:
            await _send_text(user_id, "我听到你的语音啦，但暂时没识别出内容。可以再发一次，或者直接发文字给我。")
            return
    else:
        await _send_text(user_id, f"我现在主要支持文字和语音聊天，这个“{msg_type}”消息我还接不住哦。")
        return

    if not user_text:
        return

    try:
        history = sessions.get_history(user_id)
        reply_text = await deepseek.chat(build_messages(settings, history, user_text))
        sessions.add_turn(user_id, user_text, reply_text)
    except Exception as exc:
        logger.exception("生成回复失败")
        await _send_text(user_id, "我刚刚走神了，请再试一次。")
        return

    await _send_reply(user_id, reply_text)


async def _send_reply(user_id: str, reply_text: str) -> None:
    want_voice = settings.reply_mode in {"voice", "both"} and settings.tts_enabled
    if want_voice:
        try:
            speech_text = reply_text[: settings.voice_max_chars]
            mp3_bytes = await synthesize_mp3(settings, speech_text)
            amr_bytes = convert_mp3_to_amr(settings, mp3_bytes)
            media_id = await wechat.upload_voice(amr_bytes)
            await wechat.send_customer_voice(user_id, media_id)
            if settings.reply_mode == "both":
                await wechat.send_customer_text(user_id, reply_text)
            return
        except (TTSError, WeChatClientError) as exc:
            logger.exception("语音回复失败，回退为文字")

    await _send_text(user_id, reply_text)


async def _send_text(user_id: str, content: str) -> None:
    try:
        await wechat.send_customer_text(user_id, content)
    except WeChatClientError:
        logger.exception("发送文字客服消息失败")

async def handle_message_passive(message: dict[str, str]) -> str:
    user_id = message.get("FromUserName", "")
    official_id = message.get("ToUserName", "")
    msg_type = message.get("MsgType", "").lower()

    if not user_id:
        logger.warning("\u6d88\u606f\u7f3a\u5c11 FromUserName: %s", message)
        return ""

    if message_is_event(message):
        event = message.get("Event", "").lower()
        if event == "subscribe":
            return build_text_reply(user_id, official_id, "\u55e8\uff0c\u6211\u662f " + settings.companion_name + "\uff0c\u5f88\u9ad8\u5174\u8ba4\u8bc6\u4f60\u3002\u4f60\u53ef\u4ee5\u53d1\u6587\u5b57\uff0c\u4e5f\u53ef\u4ee5\u53d1\u8bed\u97f3\u548c\u6211\u804a\u5929\u3002")
        return ""

    if msg_type == "text":
        user_text = message.get("Content", "").strip()
    elif msg_type == "voice":
        user_text = message.get("Recognition", "").strip()
        if not user_text:
            return build_text_reply(user_id, official_id, "\u6211\u542c\u5230\u4f60\u7684\u8bed\u97f3\u5566\uff0c\u4f46\u6682\u65f6\u6ca1\u8bc6\u522b\u51fa\u5185\u5bb9\u3002\u53ef\u4ee5\u518d\u53d1\u4e00\u6b21\uff0c\u6216\u8005\u76f4\u63a5\u53d1\u6587\u5b57\u7ed9\u6211\u3002")
    else:
        return build_text_reply(user_id, official_id, "\u6211\u73b0\u5728\u4e3b\u8981\u652f\u6301\u6587\u5b57\u548c\u8bed\u97f3\u804a\u5929\uff0c\u8fd9\u4e2a\u201c" + msg_type + "\u201d\u6d88\u606f\u6211\u8fd8\u63a5\u4e0d\u4f4f\u54e6\u3002")

    if not user_text:
        return ""

    try:
        history = sessions.get_history(user_id)
        reply_text = await asyncio.wait_for(
            deepseek.chat(build_messages(settings, history, user_text)),
            timeout=settings.deepseek_timeout,
        )
        sessions.add_turn(user_id, user_text, reply_text)
    except Exception:
        logger.exception("\u751f\u6210\u56de\u590d\u5931\u8d25")
        return build_text_reply(user_id, official_id, "\u6211\u521a\u521a\u8d70\u795e\u4e86\uff0c\u8bf7\u518d\u8bd5\u4e00\u6b21\u3002")

    return await _build_passive_reply(user_id, official_id, reply_text)


async def _build_passive_reply(user_id: str, official_id: str, reply_text: str) -> str:
    want_voice = settings.reply_mode in {"voice", "both"} and settings.tts_enabled
    if want_voice:
        try:
            speech_text = reply_text[: settings.voice_max_chars]
            mp3_bytes = await synthesize_mp3(settings, speech_text)
            amr_bytes = convert_mp3_to_amr(settings, mp3_bytes)
            media_id = await wechat.upload_voice(amr_bytes)
            return build_voice_reply(user_id, official_id, media_id)
        except (TTSError, WeChatClientError):
            logger.exception("\u8bed\u97f3\u56de\u590d\u5931\u8d25\uff0c\u56de\u9000\u4e3a\u6587\u5b57")

    return build_text_reply(user_id, official_id, reply_text)
