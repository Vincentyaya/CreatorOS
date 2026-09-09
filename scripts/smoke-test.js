const http = require("http");
const fs = require("fs/promises");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const PORT = 5187;
let server;
let serverError = "";

function request(path, options = {}) {
  const body = options.body ? JSON.stringify(options.body) : null;
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: "127.0.0.1",
        port: PORT,
        path,
        method: options.method || "GET",
        headers: body
          ? {
              "content-type": "application/json",
              "content-length": Buffer.byteLength(body)
            }
          : {}
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          const payload = raw ? JSON.parse(raw) : {};
          if (res.statusCode >= 400) {
            reject(new Error(payload.error || `HTTP ${res.statusCode}`));
            return;
          }
          resolve(payload);
        });
      }
    );
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

async function waitForServer() {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    try {
      await request("/api/health");
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 120));
    }
  }
  throw new Error(`Server did not start in time${serverError ? `: ${serverError}` : ""}`);
}

async function main() {
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "creatoros-smoke-"));
  const tmpDb = path.join(tmpDir, "db.json");
  await fs.copyFile(path.join(process.cwd(), "data", "db.json"), tmpDb);
  server = spawn(process.execPath, ["server.js"], {
    cwd: process.cwd(),
    env: { ...process.env, PORT: String(PORT), DB_PATH: tmpDb },
    stdio: ["ignore", "pipe", "pipe"]
  });
  server.stderr.on("data", (chunk) => {
    serverError += chunk.toString("utf8");
  });

  try {
    await waitForServer();
    const workspace = await request("/api/workspace");
    if (!workspace.trends?.length) throw new Error("Expected seed trends");
    const positioning = await request("/api/positioning", {
      method: "POST",
      body: {
        niche: "AI 内容工作流",
        audience: "独立创作者",
        strengths: "流程拆解",
        stage: "起号期",
        goal: "30 天验证赛道",
        voice: "清晰直接",
        platforms: ["小红书", "抖音"]
      }
    });
    if (!positioning.account.positioning.oneLine) throw new Error("Expected positioning result");
    const reversed = await request("/api/reverse/analyze", {
      method: "POST",
      body: {
        url: "https://example.com/hot-video",
        title: "当代打工人下班后的精神状态，被一只狗演明白了",
        platform: "抖音",
        vertical: "萌宠+脱口秀",
        targetAccount: "打工犬日记",
        transcript: "开头用反常识判断，随后用宠物表情承接打工人情绪，最后引导评论区互动。"
      }
    });
    if (!reversed.analysis?.promptPack?.scriptPrompt) throw new Error("Expected reverse prompt pack");
    const generated = await request("/api/content/generate", {
      method: "POST",
      body: { trendId: workspace.trends[0].id, platform: "小红书", format: "图文", objective: "提高收藏" }
    });
    if (!generated.draft?.id) throw new Error("Expected generated draft");
    await request(`/api/drafts/${generated.draft.id}/approve`, { method: "POST" });
    const queued = await request(`/api/publish/${generated.draft.id}`, { method: "POST", body: {} });
    if (!queued.queueItem?.id) throw new Error("Expected queue item");
    console.log("Smoke test passed");
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  } finally {
    if (server) server.kill();
    await fs.rm(tmpDir, { recursive: true, force: true });
  }
}

main();
