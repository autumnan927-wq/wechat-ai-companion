import time
from typing import Any
from xml.sax.saxutils import escape

from defusedxml.ElementTree import fromstring


def parse_message(xml_text: str) -> dict[str, str]:
    root = fromstring(xml_text)
    return {child.tag: (child.text or "").strip() for child in root}


def _reply_xml(to_user: str, from_user: str, inner_xml: str) -> str:
    create_time = int(time.time())
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{create_time}</CreateTime>"
        f"{inner_xml}"
        "</xml>"
    )


def build_text_reply(to_user: str, from_user: str, content: str) -> str:
    inner = f"<MsgType><![CDATA[text]]></MsgType><Content>{escape(content)}</Content>"
    return _reply_xml(to_user, from_user, inner)


def build_voice_reply(to_user: str, from_user: str, media_id: str) -> str:
    inner = (
        "<MsgType><![CDATA[voice]]></MsgType>"
        f"<Voice><MediaId><![CDATA[{media_id}]]></MediaId></Voice>"
    )
    return _reply_xml(to_user, from_user, inner)


def message_is_event(message: dict[str, Any]) -> bool:
    return message.get("MsgType", "").lower() == "event"
