import { useEffect, useMemo, useState } from "react"
import { PageKey, Tag } from "../shared"
import { Arrow, Check, Link, Play, Sparkle } from "../icons"
import { api, errorText, readLocal, writeLocal, type Catalog, type ReferenceVideo, type TopicPoolItem } from "../api"

const PLATFORM_META: Record<string, { name: string; color: string }> = {
  douyin: { name: "抖音", color: "#111827" },
  kuaishou: { name: "快手", color: "#f97316" },
  xhs: { name: "小红书", color: "#ef4444" },
  bili: { name: "B站", color: "#ec4899" },
  shipinhao: { name: "视频号", color: "#22c55e" },
}

const GRADS: Record<string, string> = {
  douyin: "from-indigo-500 to-violet-600",
  kuaishou: "from-amber-400 to-rose-500",
  xhs: "from-rose-400 to-orange-500",
  bili: "from-fuchsia-500 to-indigo-600",
  shipinhao: "from-emerald-400 to-teal-600",
}

const EMPTY_CATALOG: Catalog = {
  mode: "source",
  verifiedAt: "",
  notice: "仅展示已核验来源；点击封面可查看原平台内容。",
  picks: [],
  videos: [],
}

type RadarTab = "opportunities" | "feed" | "pool"
function meta(platform: string) {
  return PLATFORM_META[platform] ?? { name: platform, color: "#4f46e5" }
}

function loadPool(): TopicPoolItem[] {
  try {
    const value = readLocal("creatoros_topic_pool")
    return value ? JSON.parse(value) : []
  } catch {
    return []
  }
}

export default function Dashboard({ go }: { go: (k: PageKey) => void }) {
  const [catalog, setCatalog] = useState<Catalog>(EMPTY_CATALOG)
  const [error, setError] = useState("")
  const [tab, setTab] = useState<RadarTab>("feed")
  const [range, setRange] = useState("24h")
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set())
  const [active, setActive] = useState<ReferenceVideo | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [pool, setPool] = useState<TopicPoolItem[]>(loadPool)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let mounted = true
    api<Catalog>("/catalog?range=" + range)
      .then((data) => { if (mounted) { setCatalog(data); setError("") } })
      .catch((e) => { if (mounted) setError(errorText(e)) })
    return () => { mounted = false }
  }, [range])

  useEffect(() => {
    let mounted = true
    const local = loadPool()
    api<TopicPoolItem[]>("/topics").then(async (remote) => {
      const known = new Set(remote.map((item) => item.id))
      const missing = local.filter((item) => !known.has(item.id))
      await Promise.all(missing.map((item) => api<TopicPoolItem>("/topics", { method: "POST", body: JSON.stringify({ ...item, source: item.source ?? "trend" }) })))
      if (!mounted) return
      const merged = [...missing, ...remote]
      setPool(merged)
      writeLocal("creatoros_topic_pool", JSON.stringify(merged))
    }).catch((reason) => { if (mounted) setError(errorText(reason)) })
    return () => { mounted = false }
  }, [])

  const allPlatforms = selectedPlatforms.size === 0
  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((current) => {
      const next = new Set(current)
      next.has(platform) ? next.delete(platform) : next.add(platform)
      return next
    })
  }

  const videos = useMemo(
    () => (allPlatforms ? catalog.videos : catalog.videos.filter((video) => selectedPlatforms.has(video.platform))),
    [allPlatforms, catalog.videos, selectedPlatforms],
  )
  const picks = catalog.picks.filter((pick) => !dismissed.has(pick.topic))

  const openReference = (video: ReferenceVideo) => {
    writeLocal("creatoros_reference", JSON.stringify(video))
    go("deconstruct")
  }
  const openPick = (referenceId: string) => {
    const video = catalog.videos.find((item) => item.id === referenceId)
    if (video) openReference(video)
  }
  const usePoolItem = (item: TopicPoolItem) => {
    if (item.source === "review") {
      writeLocal("creatoros_content_topic", item.angle)
      go("generate")
      return
    }
    openPick(item.referenceId)
  }
  const addToPool = (topic: string, angle: string, referenceId: string) => {
    setPool((current) => {
      if (current.some((item) => item.referenceId === referenceId)) return current
      const item: TopicPoolItem = { id: `${referenceId}-${Date.now()}`, topic, angle, referenceId, status: "待研究", source: "trend" }
      const next = [item, ...current]
      writeLocal("creatoros_topic_pool", JSON.stringify(next))
      void api<TopicPoolItem>("/topics", { method: "POST", body: JSON.stringify(item) }).catch((reason) => setError(errorText(reason)))
      return next
    })
  }
  const removePool = (id: string) => setPool((current) => {
    const next = current.filter((item) => item.id !== id)
    writeLocal("creatoros_topic_pool", JSON.stringify(next))
    void api<{ ok: boolean }>("/topics/" + encodeURIComponent(id), { method: "DELETE" }).catch((reason) => setError(errorText(reason)))
    return next
  })
  const copyLink = () => {
    navigator.clipboard?.writeText(active?.url ?? "").catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <main className="min-h-0 min-w-0 flex-1 overflow-auto">
      <div className="mx-auto max-w-[1440px] p-6 sm:p-8 xl:p-10">
        {error && <div className="mb-5 border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-800">后端未连接，暂时无法读取热点内容。</div>}

        <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-line" aria-label="趋势雷达视图">
          {([ ["opportunities", "趋势机会"], ["feed", "热点内容流"], ["pool", `选题池${pool.length ? ` · ${pool.length}` : ""}`] ] as [RadarTab, string][]).map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} className={`border-b-2 px-0.5 pb-3 text-[14px] font-semibold transition-colors ${tab === key ? "border-primary text-primary" : "border-transparent text-sub hover:text-ink"}`}>{label}</button>
          ))}
          <label className="ml-auto flex items-center gap-2 pb-2 text-[12px] text-sub">
            时间范围
            <select value={range} onChange={(event) => setRange(event.target.value)} className="h-9 rounded-lg border border-line bg-card px-3 text-[13px] font-medium text-ink outline-none hover:border-slate-300 focus:border-primary">
              <option value="24h">近 24 小时</option>
              <option value="7d">近 7 天</option>
              <option value="30d">近 30 天</option>
            </select>
          </label>
        </nav>

        {tab === "feed" && <div className="mt-5 flex flex-wrap items-center gap-2">
          <button onClick={() => setSelectedPlatforms(new Set())} className={`px-3 py-1.5 text-[13px] font-medium ${allPlatforms ? "bg-primary text-white" : "border border-line bg-card text-sub hover:text-ink"}`}>全部平台</button>
          {Object.entries(PLATFORM_META).map(([key, platform]) => {
            const selected = selectedPlatforms.has(key)
            return <button key={key} onClick={() => togglePlatform(key)} className={`inline-flex items-center gap-1.5 border px-3 py-1.5 text-[13px] font-medium ${selected ? "border-transparent text-white" : "border-line bg-card text-sub hover:text-ink"}`} style={selected ? { backgroundColor: platform.color } : undefined}><span className="size-1.5 rounded-full" style={{ backgroundColor: selected ? "white" : platform.color }} />{platform.name}</button>
          })}
        </div>}

        {tab === "opportunities" && (
          <section className="mt-6 max-w-4xl">
            <div>
              <div className="mb-3 flex items-center justify-between"><h2 className="font-display text-[19px] font-extrabold">优先创作机会</h2><span className="text-[12px] font-mono text-sub">{picks.length} 个匹配选题</span></div>
              <div className="divide-y divide-line border-y border-line bg-card">
                {picks.map((pick, index) => {
                  const video = catalog.videos.find((item) => item.id === pick.referenceId)
                  const saved = pool.some((item) => item.referenceId === pick.referenceId)
                  return <article key={pick.topic} className="p-5 sm:p-6">
                    <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-[12px] text-sub">0{index + 1}</span><Tag tone="primary">{pick.topic}</Tag><Tag tone="success">匹配度 {pick.match}%</Tag><span className="ml-auto text-[12px] font-mono text-progress">热度 ↑ {pick.hot}</span></div>
                    <p className="mt-4 max-w-2xl text-[16px] font-semibold leading-relaxed">{pick.angle}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2 text-[12px] text-sub"><span>{video ? meta(video.platform).name : "跨平台"}</span><span>·</span><span>{video?.category ?? "AI 内容"}</span><span>·</span><span>建议在热度窗口内完成创作</span></div>
                    <div className="mt-5 flex flex-wrap gap-2">
                      <button onClick={() => openPick(pick.referenceId)} className="inline-flex items-center gap-1.5 bg-primary px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-primary/90">拆解参考 <Arrow className="size-4" /></button>
                      <button onClick={() => addToPool(pick.topic, pick.angle, pick.referenceId)} className="border border-line bg-card px-3.5 py-2 text-[13px] font-semibold text-ink hover:border-primary/40">{saved ? "已在选题池" : "加入选题池"}</button>
                      <button onClick={() => setDismissed((current) => new Set(current).add(pick.topic))} className="px-3 py-2 text-[13px] font-medium text-sub hover:text-ink">不感兴趣</button>
                    </div>
                  </article>
                })}
                {!picks.length && <div className="p-8 text-center text-[14px] text-sub">本轮机会已处理。调整平台或时间范围，继续查看。</div>}
              </div>
            </div>
          </section>
        )}

        {tab === "feed" && (
          <section className="mt-6">
            <div className="mb-3 flex flex-wrap items-end justify-between gap-2"><div><h2 className="font-display text-[19px] font-extrabold">热点内容流</h2><p className="mt-1 text-[13px] text-sub">{catalog.notice}</p></div><span className="text-[12px] font-mono text-sub">{videos.length} 条内容</span></div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {videos.map((video) => {
                const platform = meta(video.platform)
                return <article key={video.id} className="overflow-hidden border border-line bg-card transition-shadow hover:shadow-[0_18px_45px_-32px_rgba(79,70,229,0.6)]">
                  <button onClick={() => setActive(video)} className={`relative grid aspect-video w-full place-items-center bg-gradient-to-br ${GRADS[video.platform] ?? "from-indigo-500 to-violet-600"}`} aria-label={`查看 ${video.title}`}>
                    {video.poster ? <img src={video.poster} alt="" className="absolute inset-0 size-full object-cover" /> : <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(255,255,255,0.28),transparent_55%)]" />}
                    <span className="relative grid size-11 place-items-center rounded-full bg-white/20 text-white backdrop-blur"><Play className="size-6" /></span>
                    <span className="absolute left-3 top-3 px-2 py-0.5 text-[11px] font-medium text-white" style={{ backgroundColor: platform.color }}>{platform.name}</span>
                  </button>
                  <div className="p-4"><div className="flex items-center gap-1.5 text-[11px] font-mono text-primary"><Sparkle className="size-3.5" />{video.category}</div><h3 className="mt-1.5 line-clamp-2 text-[15px] font-semibold leading-snug">{video.title}</h3><p className="mt-3 text-[12px] text-sub">{video.angle}</p>{(video.author || video.likes || video.plays) && <div className="mt-4 flex items-center justify-between gap-3 font-mono text-[12px] text-sub">{video.author && <span className="truncate">{video.author}</span>}{(video.likes || video.plays) && <span className="shrink-0">{video.likes && `❤ ${video.likes}`}{video.likes && video.plays && " · "}{video.plays && `▶ ${video.plays}`}</span>}</div>}</div>
                </article>
              })}
              {!videos.length && <div className="col-span-full border-y border-line bg-card p-10 text-center text-[14px] text-sub">该平台暂无已核验内容。</div>}
            </div>
          </section>
        )}

        {tab === "pool" && <section className="mt-6 max-w-4xl"><div className="mb-3"><h2 className="font-display text-[19px] font-extrabold">账号机会池</h2></div><div className="divide-y divide-line border-y border-line bg-card">{pool.map((item) => <article key={item.id} className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex items-center gap-2"><Tag tone="primary">{item.topic}</Tag><Tag tone="ghost">{item.status}</Tag></div><p className="mt-2 text-[14px] font-medium">{item.angle}</p></div><div className="flex shrink-0 gap-2"><button onClick={() => usePoolItem(item)} className="inline-flex items-center gap-1.5 bg-primary px-3.5 py-2 text-[13px] font-semibold text-white">{item.source === "review" ? "用于创作" : "拆解"} <Arrow className="size-4" /></button><button onClick={() => removePool(item.id)} className="px-3 py-2 text-[13px] text-sub hover:text-ink">移除</button></div></article>)}{!pool.length && <div className="p-10 text-center"><p className="text-[14px] text-sub">还没有选题。去趋势机会中收集值得做的内容。</p><button onClick={() => setTab("opportunities")} className="mt-4 bg-primary px-3.5 py-2 text-[13px] font-semibold text-white">查看趋势机会</button></div>}</div></section>}
      </div>

      {active && <div className="fixed inset-0 z-50 bg-ink/35 backdrop-blur-[2px]" onClick={() => setActive(null)}><aside className="ml-auto flex h-full w-full max-w-xl flex-col overflow-auto bg-card shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className={`relative grid aspect-[16/9] place-items-center bg-gradient-to-br ${GRADS[active.platform] ?? "from-indigo-500 to-violet-600"}`}>{active.poster ? <img src={active.poster} alt="" className="absolute inset-0 size-full object-cover" /> : <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.25),transparent_55%)]" />}<a href={active.url} target="_blank" rel="noreferrer" className="relative grid size-14 place-items-center rounded-full bg-white/20 text-white backdrop-blur hover:bg-white/30" title="打开参考内容"><Play className="size-8" /></a><button onClick={() => setActive(null)} className="absolute right-4 top-4 grid size-9 place-items-center bg-black/20 text-white hover:bg-black/35" aria-label="关闭">×</button><span className="absolute left-4 top-4 px-2 py-0.5 text-[11px] font-medium text-white" style={{ backgroundColor: meta(active.platform).color }}>{meta(active.platform).name}</span></div>
        <div className="flex flex-1 flex-col p-6 sm:p-8"><div className="flex items-center gap-1.5 text-[12px] font-mono text-primary"><Sparkle className="size-4" />参考内容拆解</div><h2 className="mt-3 font-display text-[23px] font-extrabold leading-snug">{active.title}</h2>{(active.author || active.publishedAt) && <p className="mt-2 text-[13px] text-sub">{[active.author, active.publishedAt].filter(Boolean).join(" · ")}</p>}{(active.plays || active.likes) && <div className={`mt-6 grid ${active.plays && active.likes ? "grid-cols-2" : "grid-cols-1"} gap-px overflow-hidden border border-line bg-line`}>{active.plays && <div className="bg-card p-4"><div className="text-[11px] text-sub">播放</div><div className="mt-1 font-display text-[20px] font-extrabold">{active.plays}</div></div>}{active.likes && <div className="bg-card p-4"><div className="text-[11px] text-sub">点赞</div><div className="mt-1 font-display text-[20px] font-extrabold">{active.likes}</div></div>}</div>}<section className="mt-6 border-l-2 border-primary bg-primary/[0.04] px-4 py-3"><h3 className="text-[12px] font-mono text-primary">值得学习的结构</h3><p className="mt-2 text-[14px] font-semibold leading-relaxed">{active.angle}</p></section><section className="mt-5"><h3 className="text-[13px] font-semibold">创作边界</h3><p className="mt-2 text-[13px] leading-relaxed text-sub">学习选题、节奏与情绪反差；不复用原台词、原角色、画面、音乐或平台标识。</p></section><div className="mt-auto flex flex-wrap gap-2 pt-8"><button onClick={() => openReference(active)} className="inline-flex flex-1 items-center justify-center gap-2 bg-primary px-4 py-3 text-[14px] font-semibold text-white hover:bg-primary/90">开始爆款拆解 <Arrow className="size-4" /></button><button onClick={copyLink} className="inline-flex items-center justify-center gap-1.5 border border-line px-4 py-3 text-[14px] font-semibold text-ink">{copied ? <Check className="size-4 text-success" /> : <Link className="size-4" />}{copied ? "已复制" : "复制链接"}</button></div></div>
      </aside></div>}
    </main>
  )
}
