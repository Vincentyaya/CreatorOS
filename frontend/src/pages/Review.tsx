import { useEffect, useState } from "react"
import { api, errorText, readLocal, writeLocal, type TopicPoolItem } from "../api"
import { Up } from "../icons"

type Stat = { k: string; v: string; d: string }
type MetricKey = "浏览" | "点赞" | "转发" | "收藏" | "涨粉"
type Daily = { date: string; views: number; likes: number; shares: number; saves: number; followers: number }
type ReviewData = {
  mode: "demo"
  start: string
  end: string
  platform: string
  stats: Stat[]
  daily: Daily[]
  conclusion: string
  suggestion: string
}

const INITIAL_START = "2026-09-01"
const INITIAL_END = "2026-09-07"

const METRICS: Record<MetricKey, keyof Omit<Daily, "date">> = {
  浏览: "views",
  点赞: "likes",
  转发: "shares",
  收藏: "saves",
  涨粉: "followers",
}

const PLATFORMS = [
  { key: "all", name: "全部", color: "#4f46e5" },
  { key: "douyin", name: "抖音", color: "#111827" },
  { key: "kuaishou", name: "快手", color: "#f97316" },
  { key: "xhs", name: "小红书", color: "#ef4444" },
  { key: "bili", name: "B站", color: "#ec4899" },
  { key: "shipinhao", name: "视频号", color: "#22c55e" },
]

const STATS_BY: Record<string, Stat[]> = {
  all: [
    { k: "浏览", v: "4,200", d: "18%" },
    { k: "点赞", v: "386", d: "24%" },
    { k: "转发", v: "90", d: "26%" },
    { k: "收藏", v: "152", d: "31%" },
    { k: "涨粉", v: "47", d: "12%" },
  ],
  douyin: [
    { k: "浏览", v: "2,100", d: "22%" },
    { k: "点赞", v: "210", d: "28%" },
    { k: "转发", v: "54", d: "30%" },
    { k: "收藏", v: "78", d: "35%" },
    { k: "涨粉", v: "26", d: "15%" },
  ],
  kuaishou: [
    { k: "浏览", v: "620", d: "12%" },
    { k: "点赞", v: "48", d: "14%" },
    { k: "转发", v: "12", d: "15%" },
    { k: "收藏", v: "14", d: "20%" },
    { k: "涨粉", v: "6", d: "7%" },
  ],
  xhs: [
    { k: "浏览", v: "1,150", d: "16%" },
    { k: "点赞", v: "98", d: "19%" },
    { k: "转发", v: "20", d: "22%" },
    { k: "收藏", v: "52", d: "29%" },
    { k: "涨粉", v: "12", d: "9%" },
  ],
  bili: [
    { k: "浏览", v: "330", d: "9%" },
    { k: "点赞", v: "30", d: "11%" },
    { k: "转发", v: "6", d: "12%" },
    { k: "收藏", v: "8", d: "18%" },
    { k: "涨粉", v: "3", d: "6%" },
  ],
  shipinhao: [
    { k: "浏览", v: "180", d: "8%" },
    { k: "点赞", v: "14", d: "10%" },
    { k: "转发", v: "3", d: "9%" },
    { k: "收藏", v: "5", d: "16%" },
    { k: "涨粉", v: "2", d: "5%" },
  ],
}

const FALLBACK_CONCLUSION = "示例建议：测试「职场吐槽」与「轻知识」两类选题，分别记录完播率和关注转化，再决定下一轮内容配比。"
const FALLBACK_SUGGESTION = "测试职场吐槽与轻知识两类选题，以完播率和关注转化比较效果。"

function fallbackData(platform: string, start: string, end: string): ReviewData {
  const stats = STATS_BY[platform] ?? STATS_BY.all
  const daily: Daily[] = []
  const from = new Date(`${start}T00:00:00Z`).getTime()
  const to = new Date(`${end}T00:00:00Z`).getTime()
  for (let t = from; t <= to; t += 86400000) {
    const day = new Date(t)
    const views = 120 + ((day.getUTCDate() * 31 + (day.getUTCMonth() + 1) * 7) % 480)
    daily.push({
      date: day.toISOString().slice(0, 10),
      views,
      likes: Math.round(views * (0.07 + (day.getUTCDate() % 3) * 0.01)),
      shares: Math.max(1, Math.round(views * 0.018)),
      saves: Math.max(1, Math.round(views * 0.03)),
      followers: Math.max(1, Math.round(views * 0.009)),
    })
  }
  return { mode: "demo", start, end, platform, stats, daily, conclusion: FALLBACK_CONCLUSION, suggestion: FALLBACK_SUGGESTION }
}

export default function Review() {
  const [platform, setPlatform] = useState("all")
  const [start, setStart] = useState(INITIAL_START)
  const [end, setEnd] = useState(INITIAL_END)
  const [data, setData] = useState<ReviewData>(() => fallbackData("all", INITIAL_START, INITIAL_END))
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [metric, setMetric] = useState<MetricKey>("浏览")
  const [added, setAdded] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError("")
    setAdded(false)
    const query = `?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&platform=${encodeURIComponent(platform)}`
    api<ReviewData>("/review" + query)
      .then((next) => { if (!cancelled) setData(next) })
      .catch((e) => { if (!cancelled) { setData(fallbackData(platform, start, end)); setError(errorText(e)) } })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [platform, start, end])

  const metricField = METRICS[metric]
  const series = data.daily.map((day) => ({ date: day.date, value: day[metricField] ?? 0 }))
  const maxValue = Math.max(1, ...series.map((day) => day.value))

  const chartPoints = series.map((day, index) => ({
    ...day,
    x: 32 + (index / Math.max(1, series.length - 1)) * 656,
    y: 210 - (day.value / maxValue) * 170,
  }))
  const addToPool = () => {
    const referenceId = `review-${platform}-${start}-${end}`
    let pool: TopicPoolItem[] = []
    try { pool = JSON.parse(readLocal("creatoros_topic_pool") ?? "[]") } catch { pool = [] }
    if (!pool.some((item) => item.referenceId === referenceId)) {
      const item: TopicPoolItem = {
        id: `${referenceId}-${Date.now()}`,
        topic: "复盘推荐选题",
        angle: data.suggestion || data.conclusion,
        referenceId,
        status: "待研究",
        source: "review",
      }
      pool.unshift(item)
      writeLocal("creatoros_topic_pool", JSON.stringify(pool))
      void api<TopicPoolItem>("/topics", { method: "POST", body: JSON.stringify(item) }).catch((reason) => setError(errorText(reason)))
    }
    setAdded(true)
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-auto p-8 xl:p-10">
        <div className="max-w-4xl mx-auto">
          {error && (
            <div className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-700">
              后端未连接，正在显示本地数据：{error}
            </div>
          )}

          {/* filters: platform + date range */}
          <div className="flex flex-wrap items-center gap-2">
            {PLATFORMS.map((p) => {
              const on = platform === p.key
              return (
                <button
                  key={p.key}
                  onClick={() => setPlatform(p.key)}
                  className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors ${
                    on ? "border-transparent text-white" : "border border-line bg-card text-sub hover:text-ink"
                  }`}
                  style={on ? { backgroundColor: p.color } : undefined}
                >
                  <span className="size-1.5 rounded-full" style={{ backgroundColor: on ? "#fff" : p.color }} />
                  {p.name}
                </button>
              )
            })}

            <div className="ml-auto flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className="size-4 text-sub">
                <rect x="3" y="4.5" width="18" height="16" rx="2.5" />
                <path d="M3 9h18M8 3v3M16 3v3" />
              </svg>
              <input
                type="date"
                value={start}
                max={end}
                onChange={(e) => setStart(e.target.value)}
                className="bg-transparent text-[13px] text-ink font-mono outline-none"
              />
              <span className="text-sub">–</span>
              <input
                type="date"
                value={end}
                min={start}
                onChange={(e) => setEnd(e.target.value)}
                className="bg-transparent text-[13px] text-ink font-mono outline-none"
              />
            </div>
          </div>

          <div className={`mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 transition-opacity ${loading ? "opacity-60" : ""}`}>
            {data.stats.map((s) => (
              <button
                key={s.k}
                type="button"
                aria-pressed={metric === s.k}
                onClick={() => setMetric(s.k as MetricKey)}
                className={`min-h-[132px] rounded-lg border p-5 text-left outline-none transition-all focus-visible:ring-2 focus-visible:ring-primary/30 ${metric === s.k ? "border-primary bg-primary/[0.04] shadow-[inset_0_0_0_1px_rgba(79,70,229,0.12)]" : "border-line bg-card hover:border-primary/35"}`}
              >
                <div className="text-[13px] text-sub">{s.k}</div>
                <div className="mt-2 font-display font-extrabold text-[30px] leading-none">{s.v}</div>
                {s.d && (
                  <div className="mt-3 inline-flex items-center gap-1 text-[12px] font-mono font-semibold text-success">
                    <Up className="size-3.5" /> {s.d}
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* daily trend */}
          <div className="mt-6 rounded-lg border border-line bg-card p-6">
            <div>
              <div className="text-[15px] font-semibold text-ink">{metric}趋势</div>
              <div className="mt-1 text-[12px] text-sub">点击上方指标切换趋势 · 每日颗粒度</div>
            </div>
            <div className="mt-5 overflow-x-auto pb-2">
              <svg viewBox="0 0 720 240" role="img" aria-label={`${metric}每日趋势折线图`} className="h-[280px] min-w-[620px] w-full">
                {[0, 1, 2, 3, 4].map((line) => (
                  <line key={line} x1="32" x2="688" y1={40 + line * 42.5} y2={40 + line * 42.5} className="stroke-line" strokeWidth="1" />
                ))}
                <polyline points={chartPoints.map((point) => point.x + "," + point.y).join(" ")} fill="none" className="stroke-primary" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                {chartPoints.map((point) => {
                  const tooltipX = Math.min(600, Math.max(4, point.x - 58))
                  const tooltipY = Math.max(4, point.y - 48)
                  return (
                    <g key={point.date} className="group" aria-label={`${point.date}，${metric} ${point.value.toLocaleString()}`}>
                      <line x1={point.x} x2={point.x} y1="32" y2="210" stroke="transparent" strokeWidth="24" />
                      <circle cx={point.x} cy={point.y} r="5" className="fill-card stroke-primary transition-all group-hover:r-[7px]" strokeWidth="3" />
                      <g className="pointer-events-none opacity-0 transition-opacity group-hover:opacity-100">
                        <rect x={tooltipX} y={tooltipY} width="116" height="38" rx="6" className="fill-ink" />
                        <text x={tooltipX + 58} y={tooltipY + 15} textAnchor="middle" className="fill-white text-[11px] font-semibold">{metric} {point.value.toLocaleString()}</text>
                        <text x={tooltipX + 58} y={tooltipY + 29} textAnchor="middle" className="fill-white/70 text-[9px]">{point.date}</text>
                      </g>
                      <text x={point.x} y="232" textAnchor="middle" className="fill-sub text-[10px] font-mono">{point.date.slice(5)}</text>
                    </g>
                  )
                })}
              </svg>
            </div>
          </div>

          {/* conclusion */}
          <div className="mt-6 rounded-[24px] border border-primary/20 bg-gradient-to-br from-primary/[0.06] to-violet/[0.06] p-7">
            <div className="flex items-center gap-2 text-[13px] font-mono text-primary">
              <span className="size-1.5 rounded-full bg-primary animate-pulse" /> AI 复盘结论
            </div>
            <p className="mt-3 text-[19px] font-display font-bold leading-relaxed">{data.conclusion}</p>
            {data.suggestion && (
              <p className="mt-2 text-[13px] text-sub leading-relaxed">建议：{data.suggestion}</p>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              <button onClick={addToPool} className="rounded-lg bg-primary px-4 py-2.5 text-[14px] font-semibold text-white hover:bg-primary/90 transition-colors">
                {added ? "已加入选题池" : "加入选题池"}
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}
