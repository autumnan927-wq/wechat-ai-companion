from app.wechat.messages import build_text_reply, parse_message


def test_parse_message() -> None:
    xml = (
        "<xml>"
        "<ToUserName><![CDATA[toUser]]></ToUserName>"
        "<FromUserName><![CDATA[fromUser]]></FromUserName>"
        "<MsgType><![CDATA[text]]></MsgType>"
        "<Content><![CDATA[你好]]></Content>"
        "</xml>"
    )
    message = parse_message(xml)
    assert message["FromUserName"] == "fromUser"
    assert message["Content"] == "你好"


def test_build_text_reply_escapes_xml() -> None:
    reply = build_text_reply("user", "official", "hello <world> & 朋友")
    assert "<Content>hello &lt;world&gt; &amp; 朋友</Content>" in reply
