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
  const [zoomed, setZoomed] = useState(false)
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
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[15px] font-semibold text-ink">{metric}趋势</div>
                <div className="mt-1 text-[12px] text-sub">点击上方指标切换趋势</div>
              </div>
              <button type="button" onClick={() => setZoomed(true)} className="border border-line bg-card px-3 py-2 text-[13px] font-semibold text-ink transition-colors hover:border-primary/40" aria-label={`放大查看${metric}趋势`}>
                放大查看
              </button>
            </div>
            <div className="mt-4 flex items-end gap-1.5 h-24">
              {series.map((day) => (
                <div key={day.date} className="flex-1 min-w-0 group relative flex flex-col items-center justify-end" title={`${day.date} · ${metric} ${day.value.toLocaleString()}`}>
                  <div
                    className="w-full rounded-t-md bg-gradient-to-t from-primary/70 to-violet/70 group-hover:from-primary group-hover:to-violet transition-colors"
                    style={{ height: `${Math.max(8, Math.round((day.value / maxValue) * 100))}%` }}
                  />
                </div>
              ))}
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-sub">
              <span>{data.daily[0]?.date}</span>
              <span>{data.daily[data.daily.length - 1]?.date}</span>
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

      {zoomed && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4 backdrop-blur-[2px]" onClick={() => setZoomed(false)}>
          <section className="w-full max-w-5xl rounded-lg border border-line bg-card p-5 shadow-2xl sm:p-7" onClick={(event) => event.stopPropagation()} aria-modal="true" role="dialog" aria-label={`${metric}每日趋势`}>
            <div className="flex items-start justify-between gap-4">
              <div><h2 className="font-display text-[21px] font-extrabold">{metric}每日趋势</h2><p className="mt-1 text-[13px] text-sub">{start} 至 {end} · 每日颗粒度</p></div>
              <button type="button" onClick={() => setZoomed(false)} className="grid size-9 place-items-center rounded-lg text-[22px] text-sub hover:bg-canvas hover:text-ink" aria-label="关闭">×</button>
            </div>
            <div className="mt-7 overflow-x-auto pb-2">
              <div className="flex h-72 items-end gap-3" style={{ minWidth: `${Math.max(680, series.length * 72)}px` }}>
                {series.map((day) => (
                  <div key={day.date} className="flex h-full min-w-[56px] flex-1 flex-col items-center justify-end">
                    <span className="mb-2 text-[12px] font-semibold text-ink">{day.value.toLocaleString()}</span>
                    <div className="flex h-[210px] w-full items-end">
                      <div className="w-full rounded-t-md bg-primary transition-colors hover:bg-violet" style={{ height: `${Math.max(5, Math.round((day.value / maxValue) * 100))}%` }} />
                    </div>
                    <span className="mt-2 text-[11px] font-mono text-sub">{day.date.slice(5)}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
