# AI 模型接入说明（阿里云 Token Plan）

本文记录 CreatorOS 使用的阿里云 Token Plan 模型信息，供后续开发接入参考。

## ⚠️ 安全说明

- API Key 属于敏感凭据，**不要硬编码进代码，也不要提交到 Git**。
- 真实 Key 存放在 `backend/.env` 的 `QWEN_API_KEY` 中（该文件已被 `.gitignore` 忽略）。
- 若需在代码中读取，统一通过 `backend/pipeline/config.py` 的 `QWEN_API_KEY` / `require_qwen_key()`。

## 接入信息

| 项 | 值 |
| --- | --- |
| 计费方式 | 阿里云 Token Plan |
| 接入模式 | OpenAI 兼容模式（compatible-mode） |
| Base URL | `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` |
| API Key 环境变量 | `QWEN_API_KEY`（见 `backend/.env`） |

## 推荐模型映射

| 用途 | 推荐模型 |
| --- | --- |
| 文生文 | `deepseek-v4-pro-0813` |
| 文生图 / 图生图 | `qwen-image-3.0-pro` |
| 视频生成 | `happyhorse-1.1-r2v`（即 r2v） |

## 可用模型清单

### 千问 Qwen

| 模型 | 能力 |
| --- | --- |
| `qwen3.8-max`（New） | 文本生成、推理模型、视觉理解 |
| `qwen3.8-flash` | 文本生成、推理模型、视觉理解 |
| `qwen3.7-plus` | 文本生成、推理模型、视觉理解 |
| `qwen3.7-max` | 文本生成、推理模型 |
| `qwen3.6-plus` | 文本生成、推理模型、视觉理解 |
| `qwen3.6-flash` | 文本生成、推理模型、视觉理解 |
| `qwen-image-3.0-pro` | 图片生成 |
| `qwen-image-2.0` | 图片生成 |
| `qwen-image-2.0-pro` | 图片生成 |
| `qwen-audio-3.0-realtime-plus` | 实时语音对话 |
| `qwen-audio-3.0-asr-flash` | 语音识别 |
| `qwen-audio-3.0-tts-plus` | 实时语音合成、语音合成 |

### 万相 Wan

| 模型 | 能力 |
| --- | --- |
| `wan2.7-image` | 图片生成 |
| `wan2.7-image-pro` | 图片生成 |

### HappyHorse

| 模型 | 能力 |
| --- | --- |
| `happyhorse-1.1-i2v` | 视频生成（图生视频） |
| `happyhorse-1.1-t2v` | 视频生成（文生视频） |
| `happyhorse-1.1-r2v` | 视频生成（r2v） |

### DeepSeek

| 模型 | 能力 |
| --- | --- |
| `deepseek-v4-pro-0813`（限时夜间 5 折） | 文本生成、推理模型 |
| `deepseek-v4-pro` | 文本生成、推理模型 |
| `deepseek-v4-flash-0731`（限时夜间 5 折） | 文本生成、推理模型 |
| `deepseek-v4-flash` | 文本生成、推理模型 |
| `deepseek-v3.2` | 文本生成、推理模型 |

### 智谱 AI（GLM）

| 模型 | 能力 |
| --- | --- |
| `glm-5.2` | 文本生成、推理模型 |
| `glm-5.1` | 文本生成、推理模型 |
| `glm-5` | 文本生成、推理模型 |

### 月之暗面（Kimi）

| 模型 | 能力 |
| --- | --- |
| `kimi-k2.7-code` | 文本生成、推理模型、视觉理解 |
| `kimi-k2.6` | 文本生成、推理模型、视觉理解 |
| `kimi-k2.5` | 文本生成、推理模型、视觉理解 |

### MiniMax

| 模型 | 能力 |
| --- | --- |
| `MiniMax-M2.5` | 文本生成、推理模型 |

## 与后端对接说明

- 配置入口：[config.py](file:///Users/vincent/GeekVincent/Codex/CreatorOS/backend/pipeline/config.py) 读取 `QWEN_API_KEY`、`QWEN_MODEL`、`QWEN_BASE_URL`。
- 文本/视觉理解调用：[qwen_client.py](file:///Users/vincent/GeekVincent/Codex/CreatorOS/backend/pipeline/qwen_client.py) 的 `generate_json()`，可通过 `model` 参数覆盖默认模型。
- 图片生成、视频生成后端目前尚未实现；接入时分别对应推荐模型 `qwen-image-3.0-pro` 与 `happyhorse-1.1-r2v`。