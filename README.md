# CreatorOS

CreatorOS 是面向自媒体创作者的 AI 内容增长工作台。当前产品以已确认的前端 v0.1 为界面基线，后端覆盖趋势发现、爆款拆解、账号定位、内容生成、演示成片、数据复盘、选题池、待发布队列与素材包导出。

## 启动

首次运行需安装依赖：

```bash
cd frontend && pnpm install
cd ../backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

开发环境一键启动：

```bash
./scripts/start_creatoros.sh
```

浏览器访问 `http://127.0.0.1:5174/`，API 健康检查为 `http://127.0.0.1:8001/api/health`。按 `Ctrl+C` 会同时结束两个服务。

## 能力状态

- 趋势雷达：只展示已核验来源。当前为用户指定的 3 条小红书与 3 条 Bilibili 内容，卡片链接严格指向原平台，封面取自各自内容；抖音、快手和视频号没有已核验内容时显示为空。
- 爆款拆解：正式模式使用 Qwen 按关键帧逆向画面、结构与等效 Prompt。支持上传，公开平台链接在平台允许访问时由 yt-dlp 解析，受限链接会明确要求上传。
- 内容生成：演示模式可离线生成完整脚本、发布文案和视频 Prompt；正式模式使用配置的大模型。
- 角色生图：已接入当前业务空间验证可用的 `qwen-image-2.0`，生成结果保存为本地角色素材。
- 正式成片：HappyHorse 1.1 R2V，默认1080P、9:16、3–15秒，绑定角色参考图和逐镜头对白，一次生成视频、原生音频和字幕。生成失败会明确提示；重试优先复用已提交任务。演示模式仍为本地合成。
- 数据复盘：提供按浏览、点赞、评论、涨粉切换与缩放的体验数据，推荐选题可写入趋势雷达选题池。
- 发布：当前保存到待发布队列并可导出 ZIP 素材包。各平台 OAuth 未授权时不会冒充真实发布。

平台与模型配置见 `backend/.env.example`。密钥只放在后端环境文件中，不会进入浏览器或快照。

## 验证

```bash
backend/.venv/bin/python -m pytest -q backend/tests
cd frontend && pnpm exec tsc --noEmit && pnpm build
```

## 留存

单机内测部署见 `docs/DEPLOY_MINIMAL.md`。

- 已确认前端基线：`snapshots/creatoros-frontend-v0.1-2026-09-09.zip`
- 前端基线说明：`FRONTEND_V0.1_BASELINE.md`
- 当前产品交接：`PRODUCT_HANDOFF_V0.5.md`
- PRD：`docs/PRD.md`
- 上架计划：`docs/launch-plan.md`
