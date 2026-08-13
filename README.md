# 微信公众号 AI 聊天伴侣

一个可以接入微信公众号、用语音聊天的 AI 伴侣。默认使用 DeepSeek 作为对话模型，edge-tts 作为免费语音合成，FastAPI 作为微信公众号回调服务。

## 功能

- 微信公众号服务器验证与消息接收
- 文字消息对话
- 语音消息识别后对话（使用公众号的 `Recognition` 字段）
- 回复合成语音并以 AMR 上传，通过客服消息发送
- 多轮会话记忆
- 支持公众号明文模式和加密安全模式

## 目录结构

```text
app/
  main.py                 FastAPI 入口与消息路由
  config.py               配置读取
  wechat/
    crypto.py             签名校验与 AES 加解密
    messages.py           XML 解析与回复构造
    client.py             微信 API 客户端
  services/
    deepseek.py           DeepSeek 对话客户端
    chat.py               会话记忆
    tts.py                edge-tts 合成与 AMR 转换
tests/                    单元测试
```

## 本地运行

1. 安装 Python 3.11+。
2. 安装 ffmpeg，并确认支持 `libopencore_amrnb`（用于 MP3 转 AMR）。Windows 可直接使用 `winget install Gyan.FFmpeg`。
程序会优先使用 `FFMPEG_PATH`，其次查找 PATH，最后自动检测 WinGet 默认安装目录。
3. 创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

4. 复制 `.env.example` 为 `.env`，填写微信和 DeepSeek 配置；`.env` 请保存为 UTF-8，避免旧版记事本存成 ANSI。
5. 启动服务：

```powershell
python run.py
```

6. 用 Cloudflare 快速遂道暴露本地服务（ngrok 免费域名会拦截微信的浏览器 UA，不推荐）：

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

## 微信公众号配置

注意：语音回复通过客服消息发送，需要已认证的服务号（并开通客服接口权限）。如果只有订阅号，建议先把 `REPLY_MODE` 改为 `text` 验证文字聊天。

1. 在微信公众平台「设置与开发 - 基本配置」中，将服务器地址设置为 `https://你的域名/wechat`，Token 与 `.env` 中的 `WECHAT_TOKEN` 一致。
2. 明文模式：直接提交验证。加密模式：填写 EncodingAESKey 并把 `WECHAT_ENCRYPT_MODE` 设为 `true`。
3. 在公众号后台开启语音识别能力，这样语音消息 XML 会带 `Recognition` 字段；若未开启，服务会提示用户重新发送。
4. 客服消息接口要求用户 48 小时内与公众号有过互动，聊天场景下满足该条件。

## 常用配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `REPLY_MODE` | `voice` / `text` / `both` | `voice` |
| `TTS_VOICE` | edge-tts 音色 | `zh-CN-XiaoxiaoNeural` |
| `MAX_HISTORY_MESSAGES` | 每个用户保留的历史消息条数 | `16` |
| `COMPANION_NAME` | AI 伴侣名字 | `小伴` |
| `PERSONA` | 系统人设提示词，可用 `{name}` 占位 | 内置 |
| `FFMPEG_PATH` | ffmpeg 可执行文件路径；留空自动查找 | 空 |

## 测试

```powershell
pytest
```

## 云部署

推荐 Railway 或 Render，均使用项目里的 `Dockerfile`。

1. 把本项目推送到 GitHub 仓库。
2. Railway：
   - New Project -> Deploy from GitHub -> 选择仓库。
   - 会自动读取 `Dockerfile`，容器启动命令已写在 Docker 内。
   - 在 Variables 中添加和 `.env` 一致的环境变量。
3. Render：
   - New -> Web Service -> 连接 GitHub 仓库，选择 Docker runtime。
   - 项目已提供 `render.yaml`，可用 Blueprint 部署。
   - 在 Environment 中填入密钥变量。
4. 部署完成后，把服务的 HTTPS 域名加 `/wechat` 填回微信公众平台。

注意：`.env` 不要推送到 Git；云平台用环境变量注入。当前会话记忆为单实例内存存储，如后多实例扩展需改为 Redis 或数据库。
