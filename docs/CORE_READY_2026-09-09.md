# 核心内测交接

2026-09-09：真实接口链路验收通过。

- 使用项目中保留的真实上传视频，经应用API完成视频拆解（evidence=video）、Qwen原创剧本、角色绑定、HappyHorse生成、MP4下载与ZIP导出。
- HappyHorse任务：a5273a77-7912-4c7c-9ac5-8600cbc67ab2，生成约7分钟。
- 成片15.16秒，1080x1920，24fps，H.264视频与AAC立体声音轨。
- 测试应用重启后，草稿、上游任务号及成片可正常读取。
- 报告：outputs/live-tests/minimal-live-api/report.json。
- 视频：outputs/live-tests/minimal-live-api/video.mp4。
- 素材包：outputs/live-tests/minimal-live-api/package.zip。
- 8项后端测试通过，前端类型检查及生产构建通过。
- 本地8001后端已重启，实测健康检查为provider模式、最长15秒、配置1080P；5174前端仍可访问，8001也可直接提供生产前端。

范围仅为3–15秒单账号短片。超过长度的旧剧本需要精简或重新生成。失败重试优先复用provider-task.json里的任务，避免网络超时后重复付费。

边界：本次全链路采用上传输入，六条平台链接并未逐条重测；链接受限时使用上传。未做浏览器自动化全程点击验收，未人工试听新成片的每句对白。字幕、口型及内容正确性须发布前人工检查。Docker文件已提供，但本机没有Docker，未实际构建镜像或部署外部服务器。公网须使用带认证的HTTPS反向代理，当前是单账号内测。

部署步骤见docs/DEPLOY_MINIMAL.md。勿把此记录理解为所有原始验收标准均已通过。
