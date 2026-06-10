# CreatorOS 部署指南

## 架构说明

- **前端**: Vue 3 + Tailwind CSS (静态文件)
- **后端**: Python FastAPI

## 部署方案

### 方案 A: Cloudflare Pages + Railway (推荐)

#### 1. 前端部署到 Cloudflare Pages

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 进入 Pages → Create a project → Connect to Git
3. 选择 GitHub 仓库 `CreatorOS`
4. 配置:
   - Build command: 留空 (纯静态)
   - Output directory: `frontend`
5. 点击 Deploy

#### 2. 后端部署到 Railway

1. 登录 [Railway](https://railway.app)
2. New Project → Deploy from GitHub repo
3. 选择 `CreatorOS`
4. 添加环境变量:
   - `QWEN_API_KEY`: 阿里云 DashScope API Key
   - `JIMENG_ACCESS_KEY_ID`: 火山引擎 AK
   - `JIMENG_SECRET_ACCESS_KEY`: 火山引擎 SK
   - `GEMINI_API_KEY`: (可选) Google Gemini API Key
5. 设置启动命令: `python server.py`
6. 部署完成后获取域名，更新前端 API 地址

#### 3. 更新前端 API 地址

修改 `frontend/index.html` 中的 API 调用地址:
```javascript
// 将 localhost:8001 改为 Railway 域名
const API_BASE = 'https://your-railway-app.up.railway.app';
```

---

### 方案 B: 全栈部署到 Railway

直接部署整个应用到 Railway:

1. Deploy from GitHub repo
2. 设置环境变量 (同上)
3. 启动命令: `python server.py`
4. Railway 会自动暴露 8001 端口

---

### 方案 C: 本地开发

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Keys
python server.py
# 访问 http://localhost:8001
```

---

## 环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `QWEN_API_KEY` | 是 | 阿里云 DashScope API Key |
| `JIMENG_ACCESS_KEY_ID` | 是 | 火山引擎 AK |
| `JIMENG_SECRET_ACCESS_KEY` | 是 | 火山引擎 SK |
| `GEMINI_API_KEY` | 否 | Google Gemini API Key |
| `GEMINI_BASE_URL` | 否 | Gemini 中转地址 |
| `XIAOYUNQUE_TIMEOUT` | 否 | 小云雀超时 (默认 1200s) |

---

## 获取 API Keys

### 阿里云 DashScope (Qwen VL)
1. 访问 https://dashscope.console.aliyun.com/
2. 创建 API Key

### 火山引擎 (即梦/小云雀)
1. 访问 https://console.volcengine.com/
2. 开通"视觉智能"服务
3. 创建 AK/SK
4. 开通"即梦视频 3.0 Pro"和"智能生视频 Agent-Seedance 2.0"

---

## 注意事项

1. **视频生成耗时**: 小云雀生成 30s 视频约需 5-10 分钟
2. **API 限流**: 小云雀有并发限制，失败后稍等重试
3. **文件大小**: 视频会自动压缩到 1-2MB 再发送给 AI 模型
4. **存储**: runs/ 目录包含所有中间产物，建议定期清理
